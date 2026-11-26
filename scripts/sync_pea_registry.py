#!/usr/bin/env python3
"""Merge only evidence-verified PEA instruments into the market-data universe."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "data" / "pea_registry_audit.json"
DATA = ROOT / "data" / "technical_screener.json"


def merge_registry(document, audit):
    instruments = document.setdefault("instruments", [])
    by_isin = {row.get("isin"): row for row in instruments if row.get("isin")}
    added, updated = 0, 0
    for verified in audit.get("verified_instruments", []):
        if verified.get("pea_status") != "eligible":
            continue
        isin = verified.get("isin")
        if not isin:
            continue
        current = by_isin.get(isin)
        if current is None:
            current = {
                "name": verified["name"],
                "isin": isin,
                "ticker": verified["ticker"],
                "price_data_status": "pending",
                "provider_data_status": "pending",
                "provider": "Yahoo Finance (yfinance)",
            }
            instruments.append(current)
            by_isin[isin] = current
            added += 1
        else:
            updated += 1
        for field in (
            "name", "ticker", "pea_status", "pea_checked_at",
            "issuer_country_iso2", "corporate_tax_status", "instrument_type",
            "eligibility_evidence", "verified_by",
        ):
            if verified.get(field) is not None:
                current[field] = verified[field]
    document["universe_count"] = len(instruments)
    document["pea_verified_universe_count"] = sum(
        1 for row in instruments if row.get("pea_status") == "eligible"
    )
    document["registry_sync_at_utc"] = datetime.now(timezone.utc).isoformat()
    document["registry_sync_added_count"] = added
    document["registry_sync_updated_count"] = updated
    return document


def main():
    document = json.loads(DATA.read_text(encoding="utf-8"))
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    merged = merge_registry(document, audit)
    DATA.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "PEA registry sync:",
        merged["registry_sync_added_count"], "added;",
        merged["registry_sync_updated_count"], "updated;",
        merged["pea_verified_universe_count"], "verified in universe."
    )


if __name__ == "__main__":
    main()
