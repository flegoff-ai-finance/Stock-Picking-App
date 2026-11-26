#!/usr/bin/env python3
"""Audit a broker-provided or properly licensed PEA universe import.

No website scraping or automatic eligibility inference is performed here.
Rows in pea_verification.csv remain pending until all legal evidence is supplied.
"""
from __future__ import annotations

import csv
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEWS = ROOT / "data" / "pea_verification.csv"
OUTPUT = ROOT / "data" / "pea_registry_audit.json"
TECHNICAL = ROOT / "data" / "technical_screener.json"
ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{10}$")
EEA_EU_COUNTRIES = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IS", "IE", "IT", "LV", "LI", "LT", "LU",
    "MT", "NL", "NO", "PL", "PT", "RO", "SK", "SI", "ES", "SE",
}


def validate_review(row, candidate_ids, today=None):
    today = today or date.today()
    errors = []
    candidate_id = (row.get("candidate_id") or "").strip()
    if not candidate_id or candidate_id not in candidate_ids:
        errors.append("candidate_id absent ou dupliqué dans le fichier d'import")
    if not (row.get("name") or "").strip():
        errors.append("nom de l'émetteur absent")
    isin = (row.get("isin") or "").strip().upper()
    if not ISIN_RE.fullmatch(isin):
        errors.append("ISIN absent ou invalide")
    if not (row.get("ticker") or "").strip():
        errors.append("ticker Yahoo absent")
    country = (row.get("issuer_country_iso2") or "").strip().upper()
    if country not in EEA_EU_COUNTRIES:
        errors.append("siège de l'émetteur hors UE/EEE ou non confirmé")
    if (row.get("corporate_tax_status") or "").strip().lower() not in {"confirmed", "equivalent_confirmed"}:
        errors.append("assujettissement à l'impôt sur les sociétés non confirmé")
    if (row.get("instrument_type") or "").strip().lower() != "ordinary_share":
        errors.append("nature du titre non confirmée comme action ordinaire")
    for field in ("pea_eligibility_source_url", "issuer_source_url"):
        if not (row.get(field) or "").strip().startswith("https://"):
            errors.append(f"source probante manquante : {field}")
    if not (row.get("verified_by") or "").strip():
        errors.append("vérificateur non renseigné")
    try:
        checked = date.fromisoformat((row.get("verified_at") or "").strip())
        age = (today - checked).days
        if age < 0 or age > 90:
            errors.append("vérification PEA expirée ou datée dans le futur")
    except ValueError:
        errors.append("date de vérification invalide")
    return errors


def is_recently_verified_pilot(row, today):
    if row.get("pea_status") != "eligible" or not ISIN_RE.fullmatch(str(row.get("isin") or "")):
        return False
    if not (row.get("ticker") or "").strip():
        return False
    try:
        checked = date.fromisoformat(str(row.get("pea_checked_at") or "")[:10])
        age = (today - checked).days
        return 0 <= age <= 90
    except ValueError:
        return False


def build(today=None):
    today = today or date.today()
    rows = []
    if REVIEWS.exists():
        with REVIEWS.open(encoding="utf-8-sig", newline="") as stream:
            rows = [row for row in csv.DictReader(stream) if any((v or "").strip() for v in row.values())]
    ids = [row.get("candidate_id", "").strip() for row in rows]
    candidate_ids = {value for value in ids if value}
    duplicate_ids = {value for value in candidate_ids if ids.count(value) > 1}
    isins = [row.get("isin", "").strip().upper() for row in rows if row.get("isin", "").strip()]
    tickers = [row.get("ticker", "").strip().upper() for row in rows if row.get("ticker", "").strip()]
    duplicate_isins = {value for value in isins if isins.count(value) > 1}
    duplicate_tickers = {value for value in tickers if tickers.count(value) > 1}
    verified, pending = [], []
    for row in rows:
        errors = validate_review(row, candidate_ids - duplicate_ids, today)
        if row.get("candidate_id", "").strip() in duplicate_ids:
            errors.append("candidate_id dupliqué")
        if row.get("isin", "").strip().upper() in duplicate_isins:
            errors.append("ISIN dupliqué")
        if row.get("ticker", "").strip().upper() in duplicate_tickers:
            errors.append("ticker Yahoo dupliqué")
        if not errors:
            verified.append({
                "candidate_id": row["candidate_id"].strip(),
                "name": row["name"].strip(),
                "isin": row["isin"].strip().upper(),
                "ticker": row["ticker"].strip(),
                "pea_status": "eligible",
                "verification_status": "verified",
                "pea_checked_at": row["verified_at"].strip(),
                "issuer_country_iso2": row["issuer_country_iso2"].strip().upper(),
                "corporate_tax_status": row["corporate_tax_status"].strip(),
                "instrument_type": row["instrument_type"].strip(),
                "eligibility_evidence": [
                    row["pea_eligibility_source_url"].strip(),
                    row["issuer_source_url"].strip(),
                ],
                "verified_by": row["verified_by"].strip(),
            })
        else:
            pending.append({
                "candidate_id": row.get("candidate_id", "").strip(),
                "name": row.get("name", "").strip(),
                "reason": errors,
            })
    technical = json.loads(TECHNICAL.read_text(encoding="utf-8")) if TECHNICAL.exists() else {"instruments": []}
    pilot_verified = [row for row in technical.get("instruments", []) if is_recently_verified_pilot(row, today)]
    audit = {
        "schema_version": 2,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "imported_candidate_count": len(rows),
        "newly_verified_count": len(verified),
        "pending_count": len(pending),
        "legacy_verified_pilot_count": len(pilot_verified),
        "total_verified_universe_count": len(verified) + len(pilot_verified),
        "verified_pilot_names": [row.get("name") for row in pilot_verified],
        "verified_instruments": verified,
        "pending_review": pending,
        "rules": {
            "max_verification_age_days": 90,
            "required_instrument_type": "ordinary_share",
            "required_issuer_country": "EU/EEA",
            "required_tax_status": ["confirmed", "equivalent_confirmed"],
            "required_evidence": ["PEA eligibility source", "issuer source"],
        },
        "notice": "Only broker-provided or properly licensed candidate data should be imported. No website scraping is performed.",
    }
    OUTPUT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PEA registry audit: {len(verified)} new verified; {len(pending)} pending; {len(pilot_verified)} verified pilots.")
    return audit


if __name__ == "__main__":
    build()
