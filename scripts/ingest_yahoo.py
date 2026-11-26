#!/usr/bin/env python3
"""Yahoo Finance pilot ingestion for the verified PEA registry.

Uses yfinance (unofficial Yahoo Finance interface). Intended for a personal
research prototype only; check Yahoo terms/licensing before public redistribution.
"""
from __future__ import annotations

import csv
import io
import json
import math
import re
import statistics
import sys
from bisect import bisect_right
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

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


def parse_estr_csv(content):
    """Parse ECB €STR SDMX-CSV into {date: annual_rate_percent}."""
    rates = {}
    reader = csv.DictReader(io.StringIO(content))
    for row in reader:
        observed = row.get("TIME_PERIOD")
        value = number(row.get("OBS_VALUE"))
        if observed and value is not None:
            try:
                rates[date.fromisoformat(observed)] = value
            except ValueError:
                continue
    return rates


def fetch_estr_rates(start_date):
    url = (
        "https://data-api.ecb.europa.eu/service/data/EST/"
        "B.EU000A2X2A25.WT"
        f"?startPeriod={start_date.isoformat()}&format=csvdata"
    )
    request = Request(url, headers={"Accept": "text/csv", "User-Agent": "PEA-Stock-Picking-Research/1.0"})
    with urlopen(request, timeout=30) as response:
        return parse_estr_csv(response.read().decode("utf-8", errors="replace"))


def calculate_sharpe(price_points, risk_free_rates):
    """Annualized Sharpe using daily EUR €STR, carrying forward the last known rate."""
    if not risk_free_rates or len(price_points) < 200:
        return None
    rate_dates = sorted(risk_free_rates)
    excess_returns = []
    for (_, previous_close), (current_date, current_close) in zip(price_points, price_points[1:]):
        if previous_close <= 0 or current_close <= 0:
            continue
        index = bisect_right(rate_dates, current_date) - 1
        if index < 0:
            continue
        annual_rate_pct = risk_free_rates[rate_dates[index]]
        daily_rf = annual_rate_pct / 100 / 360
        excess_returns.append(current_close / previous_close - 1 - daily_rf)
    if len(excess_returns) < 200:
        return None
    deviation = statistics.stdev(excess_returns)
    if deviation == 0:
        return None
    return statistics.mean(excess_returns) / deviation * math.sqrt(252)


def calculate_relative_return(stock_points, benchmark_points, months=6):
    """Stock return minus local benchmark return over the same six-month window."""
    if len(stock_points) < 2 or len(benchmark_points) < 2:
        return None
    as_of = min(stock_points[-1][0], benchmark_points[-1][0])
    target = as_of - timedelta(days=round(months * 30.4375))

    def window_return(points):
        prior = [(day, close) for day, close in points if day <= target]
        latest = [(day, close) for day, close in points if day <= as_of]
        if not prior or not latest or prior[-1][1] <= 0:
            return None
        return latest[-1][1] / prior[-1][1] - 1

    stock_return = window_return(stock_points)
    benchmark_return = window_return(benchmark_points)
    if stock_return is None or benchmark_return is None:
        return None
    return (stock_return - benchmark_return) * 100


def benchmark_for_ticker(ticker):
    # CAC 40 is used as the current France-listed universe proxy only.
    if str(ticker).upper().endswith(".PA"):
        return {"ticker": "^FCHI", "name": "CAC 40 (proxy France)"}
    return None


def price_metrics(history, risk_free_rates=None, benchmark_history=None):
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
    stock_points = [(d.date() if hasattr(d, "date") else d, v) for d, v in zip(dates, values)]
    benchmark_points = []
    if benchmark_history is not None and not getattr(benchmark_history, "empty", True) and "Close" in benchmark_history:
        benchmark_closes = benchmark_history["Close"].dropna().sort_index()
        benchmark_points = [
            (d.date() if hasattr(d, "date") else d, float(v))
            for d, v in zip(benchmark_closes.index, benchmark_closes.tolist())
        ]
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
        "sharpe_3y": calculate_sharpe(
            [(d.date() if hasattr(d, "date") else d, v)
             for d, v in zip(dates, values)
             if (d.date() if hasattr(d, "date") else d) >= three_year_start],
            risk_free_rates or {},
        ),
        "relative_return_6m_pct": calculate_relative_return(stock_points, benchmark_points),
        "observations": len(values), "price_data_status": "ok",
    }


def growth_estimate_value(estimates, period):
    """Yahoo growth_estimates uses rows +1y/+5y and a 'stock' column."""
    if not estimates:
        return None
    try:
        stock = estimates.get("stock") or estimates.get("Stock") or {}
        value = number(stock.get(period))
        return value * 100 if value is not None else None
    except (AttributeError, TypeError):
        return None


def fundamental_metrics(info, financials, cashflow, balance, growth_estimates=None):
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
        "eps_growth_next_year_pct": growth_estimate_value(growth_estimates, "+1y"),
        # +5y is Yahoo's explicit annualized five-year analyst growth estimate.
        "eps_growth_cagr_pct": growth_estimate_value(growth_estimates, "+5y"),
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


def update_instrument(item, ticker_factory=None, risk_free_rates=None, benchmark_history=None, benchmark_info=None):
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
    item.update(price_metrics(history, risk_free_rates, benchmark_history))
    if benchmark_info:
        item["benchmark_ticker"] = benchmark_info["ticker"]
        item["benchmark_name"] = benchmark_info["name"]
    else:
        item["benchmark_ticker"] = None
        item["benchmark_name"] = None
    estimates = {}
    try:
        estimates = ticker.get_growth_estimates(as_dict=True) or {}
    except Exception:
        estimates = {}
    item.update(fundamental_metrics(info, ticker.financials, ticker.cashflow, ticker.balance_sheet, estimates))
    item["eps_growth_estimates_provider"] = "Yahoo Finance analyst growth estimates" if estimates else None
    item["risk_free_rate_provider"] = "ECB €STR" if risk_free_rates else None
    item["risk_free_rate_last_date"] = str(max(risk_free_rates)) if risk_free_rates else None
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
    try:
        risk_free_rates = fetch_estr_rates(date.today() - timedelta(days=3 * 365 + 10))
    except Exception as exc:
        risk_free_rates = {}
        document["risk_free_rate_error"] = str(exc)[:240]
        errors.append({"source": "ECB €STR", "error": str(exc)[:240]})
    benchmark_cache = {}
    for item in eligible:
        benchmark_info = benchmark_for_ticker(item.get("ticker", ""))
        benchmark_history = None
        if benchmark_info:
            benchmark_ticker = benchmark_info["ticker"]
            if benchmark_ticker not in benchmark_cache:
                try:
                    benchmark_cache[benchmark_ticker] = yf.Ticker(benchmark_ticker).history(
                        period="3y", auto_adjust=True, actions=False
                    )
                except Exception:
                    benchmark_cache[benchmark_ticker] = None
            benchmark_history = benchmark_cache[benchmark_ticker]
        try:
            update_instrument(
                item,
                risk_free_rates=risk_free_rates,
                benchmark_history=benchmark_history,
                benchmark_info=benchmark_info if benchmark_history is not None else None,
            )
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
    obsolete_notes = {
        "Yahoo one-year earnings growth is contextual only and is not substituted for the 3-5 year PEG input.",
        "Sharpe remains N/D without a dated EUR risk-free series; relative return remains N/D without verified benchmark mapping.",
        "Relative return remains N/D without a verified local benchmark mapping.",
    }
    methodology["limitations"] = [note for note in limitations if note not in obsolete_notes]
    limitations = methodology["limitations"]
    for note in [
        "Yahoo Finance via yfinance is an unofficial interface; coverage and fields vary by security.",
        "EPS growth estimates use Yahoo's explicit +1y and +5y consensus fields; +5y is the PEG growth input and is never substituted by earningsGrowth.",
        "Sharpe uses daily adjusted-price returns in excess of the ECB €STR daily series (ACT/360), annualized with sqrt(252); missing rates leave Sharpe N/D.",
        "Relative return is calculated against the CAC 40 proxy for Paris-listed pilot securities; other exchanges remain N/D until a local benchmark mapping is verified.",
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
