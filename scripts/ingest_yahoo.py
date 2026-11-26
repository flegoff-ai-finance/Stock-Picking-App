#!/usr/bin/env python3
"""Yahoo Finance pilot ingestion for the verified PEA registry.

Uses yfinance (unofficial Yahoo Finance interface). Intended for a personal
research prototype only; check Yahoo terms/licensing before public redistribution.
"""
from __future__ import annotations

import json
import math
import re
import statistics
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    yf = None

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "technical_screener.json"
ISIN_RE = re.compile(r"[A-Z]{2}[A-Z0-9]{10}")


def number(value):
    try:
        if value is None:
            return None
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def series_value(frame, *labels):
    if frame is None or getattr(frame, "empty", True):
        return None
    for label in labels:
        try:
            if label in frame.index:
                values = [number(v) for v in frame.loc[label].tolist()]
                values = [v for v in values if v is not None]
                if values:
                    return values
        except (KeyError, TypeError, AttributeError):
            pass
    return None


def cagr(values, years=3):
    values = values or []
    if len(values) < years + 1:
        return None
    old, new = number(values[years]), number(values[0])
    if old is None or new is None or old <= 0 or new <= 0:
        return None
    return ((new / old) ** (1 / years) - 1) * 100


def price_metrics(history):
    if history is None or history.empty or "Close" not in history:
        return {"price_data_status": "missing_history"}
    closes = history["Close"].dropna()
    if len(closes) < 2:
        return {"price_data_status": "insufficient_history"}
    closes = closes.sort_index()
    values = [float(v) for v in closes.tolist()]
    dates = closes.index
    latest_date = dates[-1].date() if hasattr(dates[-1], "date") else dates[-1]
    one_year_start = latest_date - timedelta(days=365)
    three_year_start = latest_date - timedelta(days=3 * 365)
    one_year = [v for d, v in zip(dates, values) if d.date() >= one_year_start]
    three_year = [v for d, v in zip(dates, values) if d.date() >= three_year_start]
    daily_returns = [values[i] / values[i-1] - 1 for i in range(1, len(values)) if values[i-1] > 0]
    one_year_returns = [one_year[i] / one_year[i-1] - 1 for i in range(1, len(one_year)) if one_year[i-1] > 0]

    def period_return(months):
        target = latest_date - timedelta(days=round(months * 30.4375))
        candidates = [(d, v) for d, v in zip(dates, values) if d.date() <= target]
        return (values[-1] / candidates[-1][1] - 1) * 100 if candidates and candidates[-1][1] > 0 else None

    def drawdown(vals):
        peak, worst = None, 0.0
        for value in vals:
            peak = value if peak is None else max(peak, value)
            if peak and peak > 0:
                worst = min(worst, (value / peak - 1) * 100)
        return worst if vals else None

    sma50 = statistics.mean(values[-50:]) if len(values) >= 50 else None
    sma200 = statistics.mean(values[-200:]) if len(values) >= 200 else None
    latest = values[-1]
    vol = statistics.stdev(one_year_returns) * math.sqrt(252) * 100 if len(one_year_returns) > 20 else None
    start_12m = [(d, v) for d, v in zip(dates, values) if d.date() <= latest_date - timedelta(days=366)]
    end_1m = [(d, v) for d, v in zip(dates, values) if d.date() <= latest_date - timedelta(days=30)]
    momentum = (end_1m[-1][1] / start_12m[-1][1] - 1) * 100 if start_12m and end_1m and start_12m[-1][1] > 0 else None
    return {
        "last_close": latest, "last_date": str(latest_date),
        "return_6m_pct": period_return(6), "return_12m_pct": period_return(12),
        "return_12_1m_pct": momentum,
        "price_vs_sma200_pct": (latest / sma200 - 1) * 100 if sma200 else None,
        "sma50_vs_sma200_pct": (sma50 / sma200 - 1) * 100 if sma50 and sma200 else None,
        "volatility_1y_pct": vol, "max_drawdown_1y_pct": drawdown(one_year),
        "max_drawdown_3y_pct": drawdown(three_year),
        "sharpe_3y": None, "relative_return_6m_pct": None,
        "observations": len(values), "price_data_status": "ok",
    }


def fundamental_metrics(info, financials, cashflow, balance):
    revenue = series_value(financials, "Total Revenue")
    ebit = series_value(financials, "Operating Income", "EBIT")
    cash_ops = series_value(cashflow, "Operating Cash Flow", "Cash Flow From Continuing Operating Activities")
    capex = series_value(cashflow, "Capital Expenditure", "Capital Expenditures")
    revenue_latest = revenue[0] if revenue else None
    ebit_latest = ebit[0] if ebit else None
    fcf = cash_ops[0] - abs(capex[0]) if cash_ops and capex else None
    debt_rows = series_value(balance, "Total Debt")
    cash_rows = series_value(balance, "Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments")
    debt = debt_rows[0] if debt_rows else None
    cash = cash_rows[0] if cash_rows else None
    ebitda_rows = series_value(financials, "EBITDA")
    ebitda = ebitda_rows[0] if ebitda_rows else None
    net_debt = debt - cash if debt is not None and cash is not None else None
    return {
        "revenue_cagr_3y_pct": cagr(revenue),
        "operating_income_cagr_3y_pct": cagr(ebit),
        "operating_margin_pct": ebit_latest / revenue_latest * 100 if ebit_latest is not None and revenue_latest else None,
        "fcf_margin_pct": fcf / revenue_latest * 100 if fcf is not None and revenue_latest else None,
        "roic_pct": None,
        "net_debt_ebitda": net_debt / ebitda if net_debt is not None and ebitda and ebitda > 0 else None,
        "forward_pe": number(info.get("forwardPE")),
        "eps_growth_next_year_pct": None,
        # Yahoo's one-year growth is never substituted for a 3-5y PEG input.
        "eps_growth_cagr_pct": None,
        "fundamental_data_status": "partial" if revenue or ebit else "missing_statements",
    }


def verified_instruments(document, today=None):
    today = today or date.today()
    result = []
    for item in document.get("instruments", []):
        try:
            checked = date.fromisoformat(str(item.get("pea_checked_at", "")))
            age = (today - checked).days
            if item.get("pea_status") == "eligible" and ISIN_RE.fullmatch(str(item.get("isin", ""))) and 0 <= age <= 90 and item.get("ticker"):
                result.append(item)
        except ValueError:
            continue
    return result


def update_instrument(item, ticker_factory=None):
    factory = ticker_factory or yf.Ticker
    ticker = factory(item["ticker"])
    history = ticker.history(period="3y", auto_adjust=True, actions=False)
    info = {}
    try:
        info = ticker.get_info() or {}
    except Exception:
        try:
            info = ticker.info or {}
        except Exception:
            info = {}
    item.update(price_metrics(history))
    item.update(fundamental_metrics(info, ticker.financials, ticker.cashflow, ticker.balance_sheet))
    item["provider"] = "Yahoo Finance (yfinance)"
    item["provider_retrieved_at_utc"] = datetime.now(timezone.utc).isoformat()
    item["provider_data_status"] = "ok" if item.get("price_data_status") == "ok" else "partial"
    item.pop("provider_error", None)


def main():
    if yf is None:
        print("Missing dependency: install yfinance>=0.2.54", file=sys.stderr)
        return 2
    document = json.loads(DATA.read_text(encoding="utf-8"))
    eligible = verified_instruments(document)
    errors = []
    for item in eligible:
        try:
            update_instrument(item)
        except Exception as exc:
            item["provider"] = "Yahoo Finance (yfinance)"
            item["provider_data_status"] = "error"
            item["provider_error"] = str(exc)[:240]
            errors.append({"ticker": item["ticker"], "error": str(exc)[:240]})
    document["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    document["data_provider"] = "Yahoo Finance (yfinance)"
    document["pea_verified_universe_count"] = len(eligible)
    document["provider_errors"] = errors
    methodology = document.setdefault("methodology", {})
    limitations = methodology.setdefault("limitations", [])
    for note in [
        "Yahoo Finance via yfinance is an unofficial interface; coverage and fields vary by security.",
        "Yahoo one-year earnings growth is contextual only and is not substituted for the 3-5 year PEG input.",
        "Sharpe remains N/D without a dated EUR risk-free series; relative return remains N/D without verified benchmark mapping.",
        "ROIC remains N/D until a consistent tax rate and invested-capital definition are available.",
        "Automated access and redistribution rights must be checked before public use.",
    ]:
        if note not in limitations:
            limitations.append(note)
    DATA.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Yahoo refresh complete: {len(eligible)} verified PEA instruments; {len(errors)} errors.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
