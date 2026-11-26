#!/usr/bin/env python3
"""Build a discovery-only European equity universe from FinanceDatabase.

This file never determines PEA eligibility and never writes to pea_verification.csv
or technical_screener.json. Every row must pass the separate evidence review.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "discovery_universe.csv"
SOURCE_REPO = "JerBouma/FinanceDatabase"
MARKETS = (
    "PAR", "AMS", "BRU", "MIL", "GER", "STO", "CPH", "HEL", "OSL",
    "LIS", "VIE", "ATH", "PRA", "BUD", "WSE", "FRA", "HAM", "MUN", "BER",
)
HOME_MARKET = {
    "France": "PAR", "Netherlands": "AMS", "Belgium": "BRU", "Italy": "MIL",
    "Germany": "GER", "Sweden": "STO", "Denmark": "CPH", "Finland": "HEL",
    "Norway": "OSL", "Portugal": "LIS", "Austria": "VIE", "Greece": "ATH",
    "Czech Republic": "PRA", "Hungary": "BUD", "Poland": "WSE",
}
COUNTRY_NAMES = {
    "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czech Republic",
    "Denmark", "Estonia", "Finland", "France", "Germany", "Greece", "Hungary",
    "Iceland", "Ireland", "Italy", "Latvia", "Liechtenstein", "Lithuania",
    "Luxembourg", "Malta", "Netherlands", "Norway", "Poland", "Portugal",
    "Romania", "Slovakia", "Slovenia", "Spain", "Sweden",
}
FIELDNAMES = [
    "candidate_id", "name", "isin", "ticker", "issuer_country", "market",
    "exchange", "currency", "market_cap", "sector", "industry", "website",
    "discovery_status", "source", "source_commit", "retrieved_at_utc",
]


def valid_isin(value: str) -> bool:
    value = (value or "").strip().upper()
    if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{10}", value):
        return False
    expanded = "".join(str(int(ch, 36)) if ch.isalpha() else ch for ch in value)
    nums = [int(ch) for ch in expanded]
    total = 0
    parity = len(nums) % 2
    for index, number in enumerate(nums):
        doubled = number * (2 if index % 2 == parity else 1)
        total += doubled // 10 + doubled % 10
    return total % 10 == 0


def _truthy_delisted(value: str) -> bool:
    return str(value or "").strip().lower() in {"true", "1", "yes", "y"}


def build_candidates(rows_by_market: dict[str, list[dict]], source_commit: str,
                     retrieved_at: str) -> list[dict]:
    market_priority = {market: index for index, market in enumerate(MARKETS)}
    selected: dict[str, dict] = {}
    for market, rows in rows_by_market.items():
        for row in rows:
            isin = (row.get("isin") or "").strip().upper()
            country = (row.get("country") or "").strip()
            ticker = (row.get("symbol") or "").strip()
            name = (row.get("name") or "").strip()
            if not valid_isin(isin) or country not in COUNTRY_NAMES:
                continue
            if _truthy_delisted(row.get("delisted")) or not ticker or not name:
                continue
            candidate = {
                "candidate_id": f"fd:{isin}",
                "name": name,
                "isin": isin,
                "ticker": ticker,
                "issuer_country": country,
                "market": (row.get("market") or "").strip(),
                "exchange": (row.get("exchange") or market).strip(),
                "currency": (row.get("currency") or "").strip(),
                "market_cap": (row.get("market_cap") or "").strip(),
                "sector": (row.get("sector") or "").strip(),
                "industry": (row.get("industry") or "").strip(),
                "website": (row.get("website") or "").strip(),
                "discovery_status": "unverified_pea",
                "source": f"https://github.com/{SOURCE_REPO}/tree/{source_commit}/database/equities",
                "source_commit": source_commit,
                "retrieved_at_utc": retrieved_at,
                "_priority": (
                    0 if HOME_MARKET.get(country) == market else 1,
                    market_priority.get(market, 999),
                ),
            }
            previous = selected.get(isin)
            if previous is None or candidate["_priority"] < previous["_priority"]:
                selected[isin] = candidate
    result = []
    for row in selected.values():
        row.pop("_priority", None)
        result.append(row)
    return sorted(result, key=lambda row: (row["issuer_country"], row["name"].casefold()))


def _get_json(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": "PEA-Stock-Picking-App/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def _get_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "PEA-Stock-Picking-App/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8-sig")


def build(output: Path = DEFAULT_OUTPUT, markets=MARKETS) -> int:
    commit = _get_json(f"https://api.github.com/repos/{SOURCE_REPO}/commits/main")["sha"]
    retrieved_at = datetime.now(timezone.utc).isoformat()
    rows_by_market = {}
    for market in markets:
        url = f"https://raw.githubusercontent.com/{SOURCE_REPO}/{commit}/database/equities/{market}.csv"
        try:
            rows_by_market[market] = list(csv.DictReader(io.StringIO(_get_text(url))))
        except Exception as exc:
            print(f"Skipping {market}: {exc}")
    if len(rows_by_market) < 6:
        raise RuntimeError(
            f"Only {len(rows_by_market)} exchange files downloaded; "
            "refusing to overwrite the previous universe."
        )
    rows = build_candidates(rows_by_market, commit, retrieved_at)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Discovery universe: {len(rows)} candidates; none promoted to PEA eligible.")
    return len(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build(args.output)
