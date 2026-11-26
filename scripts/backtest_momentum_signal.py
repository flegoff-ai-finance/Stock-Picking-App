#!/usr/bin/env python3
"""Point-in-time monthly diagnostic backtest for the Growth Momentum signal.

Only price-derived factors are used. Fundamentals and analyst estimates are
excluded because historical point-in-time snapshots are not yet available.
Raw Yahoo price history is processed in memory and is not redistributed.
"""
from __future__ import annotations

import json
import math
import statistics
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    yf = None

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.ingest_yahoo import fetch_estr_rates, price_metrics, verified_instruments

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "technical_screener.json"
OUTPUT = ROOT / "data" / "backtest_momentum.json"
FACTORS = [
    ("return_12_1m_pct", 25, False),
    ("return_6m_pct", 15, False),
    ("price_vs_sma200_pct", 15, False),
    ("sma50_vs_sma200_pct", 10, False),
    ("sharpe_3y", 10, False),
    ("max_drawdown_1y_pct", 10, False),
    ("volatility_1y_pct", 5, True),
    ("relative_return_6m_pct", 10, False),
]
HORIZONS = {"1m": 21, "3m": 63, "6m": 126}
FEE_RATE = 0.005


def percentile(values, value, lower_is_better=False):
    valid = sorted(v for v in values if v is not None and math.isfinite(v))
    if value is None or not valid:
        return None
    if len(valid) == 1:
        return 50.0
    below = sum(1 for v in valid if v < value)
    equal = sum(1 for v in valid if v == value)
    result = 100 * (below + (equal - 1) / 2) / (len(valid) - 1)
    return 100 - result if lower_is_better else result


def score_snapshot(metrics_by_ticker):
    scores = {}
    for ticker, metrics in metrics_by_ticker.items():
        components, present_weight = [], 0
        for field, weight, lower in FACTORS:
            value = metrics.get(field)
            if value is None:
                continue
            cohort = [m.get(field) for m in metrics_by_ticker.values()]
            rank = percentile(cohort, value, lower)
            if rank is not None:
                components.append((rank, weight))
                present_weight += weight
        if len(components) >= 4 and present_weight >= 75:
            scores[ticker] = sum(rank * weight for rank, weight in components) / present_weight
    return scores


def future_return(history, cutoff, horizon_days):
    closes = history["Close"].dropna().sort_index()
    index = closes.index.get_indexer([cutoff], method="pad")[0]
    future_index = index + horizon_days
    if index < 0 or future_index >= len(closes):
        return None
    start, end = float(closes.iloc[index]), float(closes.iloc[future_index])
    if start <= 0:
        return None
    return end / start - 1


def rank_correlation(scores, returns):
    common = [key for key in scores if returns.get(key) is not None]
    if len(common) < 4:
        return None
    score_ranks = [percentile([scores[k] for k in common], scores[k]) for k in common]
    return_ranks = [percentile([returns[k] for k in common], returns[k]) for k in common]
    mean_x, mean_y = statistics.mean(score_ranks), statistics.mean(return_ranks)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(score_ranks, return_ranks))
    denominator = math.sqrt(
        sum((x - mean_x) ** 2 for x in score_ranks) *
        sum((y - mean_y) ** 2 for y in return_ranks)
    )
    return numerator / denominator if denominator else None


def summarize_observations(observations):
    if not observations:
        return {"snapshots": 0, "rank_correlation": None, "top2_avg_return_pct": None,
                "top2_avg_net_return_pct": None, "top2_positive_rate_pct": None,
                "top2_minus_bottom2_spread_pct": None}
    correlations = [x["correlation"] for x in observations if x["correlation"] is not None]
    top_returns = [x["top2_avg_return"] for x in observations if x["top2_avg_return"] is not None]
    top_net = [x["top2_avg_net_return"] for x in observations if x["top2_avg_net_return"] is not None]
    positive = [x["top2_positive_rate"] for x in observations if x["top2_positive_rate"] is not None]
    spreads = [x["spread"] for x in observations if x["spread"] is not None]
    mean = lambda values: round(statistics.mean(values) * 100, 2) if values else None
    return {
        "snapshots": len(observations),
        "rank_correlation": round(statistics.mean(correlations), 3) if correlations else None,
        "top2_avg_return_pct": mean(top_returns),
        "top2_avg_net_return_pct": mean(top_net),
        "top2_positive_rate_pct": mean(positive),
        "top2_minus_bottom2_spread_pct": mean(spreads),
    }


def run_backtest(instruments, ticker_factory=None, estr_rates=None):
    factory = ticker_factory or yf.Ticker
    eligible = verified_instruments({"instruments": instruments})
    if not eligible:
        raise RuntimeError("No recently verified PEA instruments available for backtest.")
    histories = {}
    for item in eligible:
        ticker = factory(item["ticker"])
        history = ticker.history(period="3y", auto_adjust=True, actions=False)
        if history is not None and not history.empty and "Close" in history:
            histories[item["ticker"]] = history
    if len(histories) < 4:
        raise RuntimeError("At least four securities with usable price history are required.")
    benchmark_history = factory("^FCHI").history(period="3y", auto_adjust=True, actions=False)
    if benchmark_history is None or benchmark_history.empty:
        raise RuntimeError("CAC 40 benchmark history unavailable.")
    common_dates = sorted(set.intersection(*[
        set(history.index.to_list()) for history in histories.values()
    ]))
    if not common_dates:
        raise RuntimeError("No common trading dates across pilot securities.")
    monthly_cutoffs = []
    previous_month = None
    for timestamp in common_dates:
        month = (timestamp.year, timestamp.month)
        if month != previous_month and monthly_cutoffs:
            monthly_cutoffs[-1] = previous_timestamp
        if month != previous_month:
            monthly_cutoffs.append(timestamp)
            previous_month = month
        previous_timestamp = timestamp
    if monthly_cutoffs:
        monthly_cutoffs[-1] = previous_timestamp

    results = {horizon: [] for horizon in HORIZONS}
    for cutoff in monthly_cutoffs:
        metrics_by_ticker = {}
        for ticker, history in histories.items():
            sliced = history.loc[:cutoff]
            benchmark_slice = benchmark_history.loc[:cutoff]
            metrics = price_metrics(sliced, estr_rates or {}, benchmark_slice)
            if metrics.get("price_data_status") == "ok":
                metrics_by_ticker[ticker] = metrics
        scores = score_snapshot(metrics_by_ticker)
        if len(scores) < 4:
            continue
        ranked = sorted(scores, key=scores.get, reverse=True)
        for label, horizon in HORIZONS.items():
            returns = {
                ticker: future_return(histories[ticker], cutoff, horizon)
                for ticker in scores
            }
            valid = {ticker: value for ticker, value in returns.items() if value is not None}
            if len(valid) < 4:
                continue
            top = ranked[:2]
            bottom = ranked[-2:]
            top_values = [valid[t] for t in top if t in valid]
            bottom_values = [valid[t] for t in bottom if t in valid]
            if not top_values or not bottom_values:
                continue
            net_values = [((1 + value) * (1 - FEE_RATE) ** 2) - 1 for value in top_values]
            results[label].append({
                "correlation": rank_correlation(scores, valid),
                "top2_avg_return": statistics.mean(top_values),
                "top2_avg_net_return": statistics.mean(net_values),
                "top2_positive_rate": sum(1 for value in top_values if value > 0) / len(top_values),
                "spread": statistics.mean(top_values) - statistics.mean(bottom_values),
            })
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "strategy": "Growth Momentum",
        "method": "Monthly point-in-time cross-sectional rank diagnostic; top 2 versus bottom 2; no fundamental factors.",
        "universe_count": len(histories),
        "universe": "verified PEA pilot securities only",
        "rebalance_frequency": "monthly diagnostic snapshots",
        "rank_correlation_method": "Spearman correlation (Pearson correlation of cross-sectional percentile ranks), averaged across monthly snapshots",
        "transaction_fee_each_side_pct": FEE_RATE * 100,
        "benchmark": "CAC 40 (^FCHI), France-listed pilot universe proxy",
        "history_start": str(common_dates[0].date() if hasattr(common_dates[0], "date") else common_dates[0]),
        "history_end": str(common_dates[-1].date() if hasattr(common_dates[-1], "date") else common_dates[-1]),
        "limitations": [
            "Only the seven current pilot securities are in scope; this is not a market-wide backtest.",
            "The score is cross-sectional and uses only information available on each monthly cutoff.",
            "Top-two and bottom-two groups are signal diagnostics, not the approved virtual-portfolio construction.",
            "Quality and Growth are not backtested because historical point-in-time fundamentals and analyst estimates are unavailable.",
            "Results are gross signal statistics except the top-two average, which also reports a hypothetical 0.5% fee on entry and exit.",
        ],
        "horizons": {label: summarize_observations(rows) for label, rows in results.items()},
        "monthly_snapshots": len(monthly_cutoffs),
    }


def main():
    if yf is None:
        print("Missing dependency: install yfinance>=0.2.54", file=sys.stderr)
        return 2
    document = json.loads(DATA.read_text(encoding="utf-8"))
    try:
        rates = fetch_estr_rates(date.today() - timedelta(days=3 * 365 + 10))
    except Exception as exc:
        rates = {}
        print(f"ECB €STR unavailable; Sharpe factors will be omitted: {exc}", file=sys.stderr)
    result = run_backtest(document.get("instruments", []), estr_rates=rates)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Momentum backtest complete:", json.dumps(result["horizons"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
