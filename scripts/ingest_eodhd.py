#!/usr/bin/env python3
"""Build a transparent strategy-data snapshot from EODHD.

The input registry remains the source of truth for PEA eligibility. This script
never discovers or promotes securities into the eligible universe.
"""
from __future__ import annotations

import json
import math
import os
import statistics
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "technical_screener.json"
OUTPUT = ROOT / "data" / "technical_screener.json"
BASE_URL = "https://eodhd.com/api"
TOKEN = os.environ.get("EODHD_API_TOKEN", "").strip()
USER_AGENT = "pea-stock-picking-research/1.0"


def request_json(path: str, params: dict) -> object:
    query = urlencode({**params, "api_token": TOKEN, "fmt": "json"})
    request = Request(f"{BASE_URL}/{path}?{query}", headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=35) as response:
            payload = response.read().decode("utf-8")
        data = json.loads(payload)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"EODHD request failed for {path}: {exc}") from exc
    if isinstance(data, dict) and (data.get("error") or data.get("message") == "Forbidden"):
        raise RuntimeError(f"EODHD returned an error for {path}: {data}")
    return data


def as_float(value):
    try:
        if value is None or value == "":
            return None
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def first_number(obj: dict, *keys):
    for key in keys:
        value = as_float(obj.get(key))
        if value is not None:
            return value
    return None


def dated_rows(section):
    if not isinstance(section, dict):
        return []
    rows = []
    for key, value in section.items():
        if isinstance(value, dict):
            stamp = str(value.get("date") or key)
            if len(stamp) >= 4 and stamp[:4].isdigit():
                rows.append((stamp, value))
    rows.sort(key=lambda item: item[0])
    return rows


def cagr(rows, aliases, years=3):
    if len(rows) < years + 1:
        return None
    old = first_number(rows[-(years + 1)][1], *aliases)
    new = first_number(rows[-1][1], *aliases)
    if old is None or new is None or old <= 0 or new <= 0:
        return None
    return ((new / old) ** (1 / years) - 1) * 100


def pct_change(series, months):
    if len(series) < 2:
        return None
    target = series[-1][0].date() - timedelta(days=round(months * 30.4375))
    candidates = [row for row in series if row[0].date() <= target]
    if not candidates:
        return None
    base = candidates[-1][1]
    return (series[-1][1] / base - 1) * 100 if base > 0 else None


def max_drawdown(series):
    peak = None
    worst = 0.0
    for _, price in series:
        peak = price if peak is None else max(peak, price)
        if peak and peak > 0:
            worst = min(worst, (price / peak - 1) * 100)
    return worst if series else None


def price_metrics(history):
    rows = []
    for item in history if isinstance(history, list) else []:
        try:
            stamp = datetime.strptime(item["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            close = as_float(item.get("adjusted_close")) or as_float(item.get("close"))
            if close is not None and close > 0:
                rows.append((stamp, close))
        except (KeyError, TypeError, ValueError):
            continue
    rows.sort(key=lambda row: row[0])
    if len(rows) < 2:
        return {"price_data_status": "insufficient_history"}
    today = rows[-1][0].date()
    one_year = [r for r in rows if r[0].date() >= today - timedelta(days=366)]
    three_year = [r for r in rows if r[0].date() >= today - timedelta(days=3 * 366)]
    closes = [r[1] for r in rows]
    returns = [(closes[i] / closes[i - 1] - 1) for i in range(1, len(closes)) if closes[i - 1] > 0]
    returns_1y = [(one_year[i][1] / one_year[i - 1][1] - 1) for i in range(1, len(one_year)) if one_year[i - 1][1] > 0]
    sma50 = statistics.mean(closes[-50:]) if len(closes) >= 50 else None
    sma200 = statistics.mean(closes[-200:]) if len(closes) >= 200 else None
    latest = closes[-1]
    vol = statistics.stdev(returns_1y) * math.sqrt(252) * 100 if len(returns_1y) > 20 else None
    return {
        "last_close": latest,
        "last_date": rows[-1][0].date().isoformat(),
        "return_6m_pct": pct_change(rows, 6),
        "return_12m_pct": pct_change(rows, 12),
        "return_12_1m_pct": (pct_change(rows, 11) if pct_change(rows, 12) is not None else None),
        "price_vs_sma200_pct": (latest / sma200 - 1) * 100 if sma200 else None,
        "sma50_vs_sma200_pct": (sma50 / sma200 - 1) * 100 if sma50 and sma200 else None,
        "volatility_1y_pct": vol,
        "max_drawdown_1y_pct": max_drawdown(one_year),
        "max_drawdown_3y_pct": max_drawdown(three_year),
        # Sharpe needs a dated EUR risk-free series; do not silently assume 0%.
        "sharpe_3y": None,
        # Relative return needs a verified local benchmark mapping per instrument.
        "relative_return_6m_pct": None,
        "observations": len(rows),
        "price_data_status": "ok",
    }


def fundamental_metrics(raw):
    financials = raw.get("Financials") or {}
    income = financials.get("Income_Statement") or {}
    cashflow = financials.get("Cash_Flow") or {}
    balance = financials.get("Balance_Sheet") or {}
    income_rows = dated_rows(income.get("yearly") or income.get("yearly_last_0") or {})
    cash_rows = dated_rows(cashflow.get("yearly") or {})
    balance_rows = dated_rows(balance.get("yearly") or {})
    latest_income = income_rows[-1][1] if income_rows else {}
    latest_cash = cash_rows[-1][1] if cash_rows else {}
    latest_balance = balance_rows[-1][1] if balance_rows else {}
    revenue = first_number(latest_income, "totalRevenue", "totalRevenueReported", "revenue")
    ebit = first_number(latest_income, "operatingIncome", "ebit", "EBIT")
    ebitda = first_number(latest_income, "ebitda", "EBITDA")
    operating_cash = first_number(latest_cash, "totalCashFromOperatingActivities", "operatingCashFlow", "cashFromOperatingActivities")
    capex = first_number(latest_cash, "capitalExpenditures", "capitalExpenditure", "capex")
    cash = first_number(latest_balance, "cashAndCashEquivalents", "cash", "cashAndShortTermInvestments") or 0
    debt = first_number(latest_balance, "shortLongTermDebtTotal", "totalDebt")
    if debt is None:
        short_debt = first_number(latest_balance, "shortTermDebt") or 0
        long_debt = first_number(latest_balance, "longTermDebt") or 0
        debt = short_debt + long_debt if short_debt or long_debt else None
    net_debt = debt - cash if debt is not None else None
    fcf = operating_cash - abs(capex) if operating_cash is not None and capex is not None else None
    ev = raw.get("Valuation") or {}
    highlights = raw.get("Highlights") or {}
    valuation = raw.get("Valuation") or {}
    forward_pe = first_number(valuation, "ForwardPE") or first_number(highlights, "ForwardPE")
    trend = raw.get("Earnings", {}).get("Trend", []) if isinstance(raw.get("Earnings"), dict) else []
    if isinstance(trend, dict):
        trend = list(trend.values())
    next_year_growth = None
    if isinstance(trend, list):
        for row in trend:
            if isinstance(row, dict) and row.get("period") == "+1y":
                next_year_growth = as_float(row.get("growth"))
                break
    if next_year_growth is not None and abs(next_year_growth) <= 2:
        next_year_growth *= 100
    tax_rate = None
    tax = first_number(latest_income, "incomeTaxExpense", "taxProvision")
    pretax = first_number(latest_income, "incomeBeforeTax", "pretaxIncome")
    if tax is not None and pretax and pretax > 0:
        tax_rate = max(0, min(0.5, tax / pretax))
    invested = None
    equity = first_number(latest_balance, "totalStockholderEquity", "totalStockholdersEquity", "totalEquity")
    if debt is not None and equity is not None:
        invested = debt + equity - cash
    roic = (ebit * (1 - (tax_rate if tax_rate is not None else 0.25)) / invested * 100) if ebit is not None and invested and invested > 0 else None
    return {
        "revenue_cagr_3y_pct": cagr(income_rows, ("totalRevenue", "totalRevenueReported", "revenue")),
        "operating_income_cagr_3y_pct": cagr(income_rows, ("operatingIncome", "ebit", "EBIT")),
        "operating_margin_pct": ebit / revenue * 100 if ebit is not None and revenue else None,
        "fcf_margin_pct": fcf / revenue * 100 if fcf is not None and revenue else None,
        "roic_pct": roic,
        "net_debt_ebitda": net_debt / ebitda if net_debt is not None and ebitda and ebitda > 0 else None,
        "forward_pe": forward_pe,
        # +1y is displayed for context, but is NOT substituted for the classic 3-5y PEG growth input.
        "eps_growth_next_year_pct": next_year_growth,
        "eps_growth_cagr_pct": None,
        "fundamental_data_status": "ok" if income_rows else "missing_statements",
    }


def main():
    if not TOKEN:
        print("EODHD_API_TOKEN is missing; no data was changed.", file=sys.stderr)
        return 2
    if not INPUT.exists():
        print(f"Missing input registry: {INPUT}", file=sys.stderr)
        return 2
    document = json.loads(INPUT.read_text(encoding="utf-8"))
    instruments = document.get("instruments", [])
    today = date.today()
    eligible = []
    for item in instruments:
        try:
            checked = date.fromisoformat(str(item.get("pea_checked_at", "")))
            valid_isin = len(str(item.get("isin", ""))) == 12
            if item.get("pea_status") == "eligible" and valid_isin and 0 <= (today - checked).days <= 90:
                eligible.append(item)
        except ValueError:
            continue
    errors = []
    for item in eligible:
        ticker = str(item.get("ticker", "")).strip()
        if not ticker:
            continue
        try:
            history = request_json(f"eod/{ticker}", {"from": (today - timedelta(days=3 * 366)).isoformat(), "to": today.isoformat(), "period": "d", "order": "a"})
            fundamentals = request_json(f"fundamentals/{ticker}", {"filter": "General,Highlights,Valuation,Technicals,Earnings,Financials"})
            item.update(price_metrics(history))
            item.update(fundamental_metrics(fundamentals if isinstance(fundamentals, dict) else {}))
            item["provider"] = "EODHD"
            item["provider_retrieved_at_utc"] = datetime.now(timezone.utc).isoformat()
        except Exception as exc:  # Keep the rest of the universe usable when one symbol fails.
            item["provider_data_status"] = "error"
            item["provider_error"] = str(exc)[:240]
            errors.append({"ticker": ticker, "error": str(exc)[:240]})
        time.sleep(0.15)
    document["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    document["data_provider"] = "EODHD"
    document["pea_verified_universe_count"] = len(eligible)
    document["provider_errors"] = errors
    document["methodology"] = document.get("methodology", {})
    limitations = document["methodology"].setdefault("limitations", [])
    additions = [
        "PEA eligibility is inherited from the verified input registry; provider data never changes eligibility.",
        "EODHD +1y earnings growth is stored for context but is not used as a substitute for 3–5 year PEG growth.",
        "Sharpe requires a dated EUR risk-free series; relative momentum requires a verified local benchmark mapping. Both remain N/D until supplied.",
        "Missing financial statement fields remain null; no synthetic values are imputed.",
    ]
    for note in additions:
        if note not in limitations:
            limitations.append(note)
    OUTPUT.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {OUTPUT.name}: {len(eligible)} PEA-verified instruments; {len(errors)} provider errors.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
