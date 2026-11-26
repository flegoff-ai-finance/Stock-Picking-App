#!/usr/bin/env python3
"""Build a strict audit of PEA candidate verification decisions."""
from __future__ import annotations

import csv
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "data" / "pea_candidates.json"
REVIEWS = ROOT / "data" / "pea_verification.csv"
OUTPUT = ROOT / "data" / "pea_registry_audit.json"
ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{10}$")
EEA_EU_COUNTRIES = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IS", "IE", "IT", "LV", "LI", "LT", "LU",
    "MT", "NL", "NO", "PL", "PT", "RO", "SK", "SI", "ES", "SE",
}
REVIEW_FIELDS = [
    "candidate_id", "isin", "ticker", "issuer_country_iso2",
    "corporate_tax_status", "instrument_type", "pea_eligibility_source_url",
    "issuer_source_url", "verified_by", "verified_at",
]


def validate_review(row, candidate_ids, today=None):
    today = today or date.today()
    errors = []
    candidate_id = (row.get("candidate_id") or "").strip()
    if candidate_id not in candidate_ids:
        errors.append("candidate_id absent du référentiel de découverte")
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


def build(today=None):
    today = today or date.today()
    document = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    candidate_ids = {row["candidate_id"] for row in document.get("candidates", [])}
    reviews = {}
    if REVIEWS.exists():
        with REVIEWS.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if row.get("candidate_id"):
                    reviews[row["candidate_id"].strip()] = row
    verified, pending = [], []
    for candidate in document.get("candidates", []):
        review = reviews.get(candidate["candidate_id"])
        errors = ["aucune revue documentée"] if review is None else validate_review(review, candidate_ids, today)
        if not errors:
            verified.append({
                **candidate,
                "isin": review["isin"].strip().upper(),
                "ticker": review["ticker"].strip(),
                "pea_status": "eligible",
                "verification_status": "verified",
                "pea_checked_at": review["verified_at"].strip(),
                "issuer_country_iso2": review["issuer_country_iso2"].strip().upper(),
                "corporate_tax_status": review["corporate_tax_status"].strip(),
                "instrument_type": review["instrument_type"].strip(),
                "eligibility_evidence": [
                    review["pea_eligibility_source_url"].strip(),
                    review["issuer_source_url"].strip(),
                ],
                "verified_by": review["verified_by"].strip(),
            })
        else:
            pending.append({
                "candidate_id": candidate["candidate_id"],
                "name": candidate["name"],
                "reason": errors,
            })
    audit = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_count": len(document.get("candidates", [])),
        "verified_count": len(verified),
        "pending_count": len(pending),
        "verified_instruments": verified,
        "pending_review": pending,
        "rules": {
            "max_verification_age_days": 90,
            "required_instrument_type": "ordinary_share",
            "required_issuer_country": "EU/EEA",
            "required_tax_status": ["confirmed", "equivalent_confirmed"],
            "required_evidence": ["PEA eligibility source", "issuer source"],
        },
    }
    OUTPUT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PEA registry audit: {len(verified)} verified; {len(pending)} pending.")
    return audit


if __name__ == "__main__":
    build()
