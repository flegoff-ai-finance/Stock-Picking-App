#!/usr/bin/env python3
"""Discover listed equity candidates from ProRealTime's public PEA instrument directories.

Discovery is deliberately NOT proof of legal PEA eligibility. All imported rows
are marked pending and are excluded from scoring until separately verified.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "pea_candidates.json"
SOURCES = {
    "france": "https://www.prorealtime.com/fr/financial-instruments/actions-eligibles-pea",
    "europe": "https://www.prorealtime.com/fr/financial-instruments/actions-europe-eligibles-pea",
    "eee": "https://www.prorealtime.com/fr/financial-instruments/actions-eee-eligibles-pea",
    "meqiri": "https://meqiri.com/fr/actions/eligibles-pea",
}
MEQIRI_TICKER_RE = re.compile(r"^(?P<name>.+?)\s+(?P<ticker>[A-Z0-9][A-Z0-9.\-]{0,20}\.(?:PA|DE|F|AS|MC|MI|BR|ST|CO|OL|HE|WA|VI|AT|IR|LS|PR|IS|BD|RO))$")
COUNTRY_CODES = {
    "France": "FR", "Allemagne": "DE", "Pays-Bas": "NL", "Grèce": "GR",
    "Suède": "SE", "Pologne": "PL", "Finlande": "FI", "Espagne": "ES",
    "Italie": "IT", "Belgique": "BE", "Danemark": "DK", "Norvège": "NO",
    "Irlande": "IE", "Autriche": "AT", "Malte": "MT", "Chypre": "CY",
    "Slovénie": "SI", "Luxembourg": "LU", "Estonie": "EE", "Lettonie": "LV",
    "Lituanie": "LT", "Tchéquie": "CZ", "Croatie": "HR", "Hongrie": "HU",
    "Bulgarie": "BG", "Islande": "IS", "Liechtenstein": "LI", "Portugal": "PT",
    "Roumanie": "RO", "Slovaquie": "SK",
}
MARKET_SUFFIX = {
    "xpar": ".PA", "xams": ".AS", "xbru": ".BR", "xdub": ".IR",
    "xlis": ".LS", "xmil": ".MI", "xosl": ".OL", "xetr": ".DE",
    "xfra": ".DE", "xmce": ".MC", "xsto": ".ST", "xhel": ".HE",
    "xcse": ".CO", "xwar": ".WA",
}


class ListingParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.cell = None
        self.row = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "table":
            self.in_table = True
        elif self.in_table and tag == "tr":
            self.in_row, self.row = True, []
        elif self.in_row and tag in ("td", "th"):
            self.in_cell = True
            self.cell = {"text": [], "href": None}
        elif self.in_cell and tag == "a" and attrs.get("href"):
            self.cell["href"] = attrs["href"]

    def handle_data(self, data):
        if self.in_cell and self.cell is not None:
            value = " ".join(data.split())
            if value:
                self.cell["text"].append(value)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.in_cell:
            self.row.append(self.cell)
            self.cell, self.in_cell = None, False
        elif tag == "tr" and self.in_row:
            if len(self.row) >= 2:
                self.rows.append(self.row)
            self.in_row, self.row = False, []
        elif tag == "table":
            self.in_table = False


def fetch(url):
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; PEAResearch/1.0)"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_listing(html, region, source_url):
    parser = ListingParser()
    parser.feed(html)
    rows = []
    for cells in parser.rows:
        code = " ".join(cells[0]["text"]).strip()
        name = " ".join(cells[1]["text"]).strip()
        if not code or not name or code.lower() in {"code", "ticker", "symbole"} or name.lower() in {"nom", "name"}:
            continue
        href = cells[1].get("href")
        market = None
        if href:
            match = re.search(r"/web/([a-z0-9]+)-", href.lower())
            market = match.group(1) if match else None
        suffix = MARKET_SUFFIX.get(market)
        ticker = f"{code}{suffix}" if suffix else None
        identity = f"{region}|{market or ''}|{code}|{name}".lower()
        rows.append({
            "candidate_id": hashlib.sha1(identity.encode("utf-8")).hexdigest()[:16],
            "name": name,
            "source_code": code,
            "source_market": market,
            "provisional_yahoo_ticker": ticker,
            "isin": None,
            "pea_status": "pending_verification",
            "verification_status": "not_verified",
            "source": "ProRealTime PEA instrument directory",
            "source_region": region,
            "source_url": source_url,
            "source_instrument_url": href,
            "eligibility_evidence": [],
            "exclusion_reason": None,
        })
    return rows


def parse_meqiri_listing(html, source_url):
    parser = ListingParser()
    parser.feed(html)
    rows = []
    for cells in parser.rows:
        texts = [" ".join(cell["text"]).strip() for cell in cells]
        name, ticker, href = None, None, None
        for index, value in enumerate(texts):
            match = MEQIRI_TICKER_RE.fullmatch(value)
            if match:
                name, ticker = match.group("name").strip(), match.group("ticker")
                href = cells[index].get("href")
                break
            if re.fullmatch(r"[A-Z0-9][A-Z0-9.\-]{0,20}\.(?:PA|DE|F|AS|MC|MI|BR|ST|CO|OL|HE|WA|VI|AT|IR|LS|PR|IS|BD|RO)", value):
                ticker = value
                name = texts[index - 1] if index > 0 else None
                href = cells[index - 1].get("href") if index > 0 else cells[index].get("href")
                break
        if not name or not ticker:
            continue
        country_hint = next((code for country, code in COUNTRY_CODES.items()
                             if any(country.casefold() == value.casefold() for value in texts)), None)
        market = ticker.rsplit(".", 1)[-1]
        rows.append({
            "candidate_id": hashlib.sha1(("MEQIRI|" + ticker).encode("utf-8")).hexdigest()[:16],
            "name": name,
            "source_code": ticker.rsplit(".", 1)[0],
            "source_market": market,
            "provisional_yahoo_ticker": ticker,
            "isin": None,
            "pea_status": "pending_verification",
            "verification_status": "prequalified_pending_legal_review",
            "source": "MEQIRI PEA list",
            "source_region": "meqiri",
            "source_url": source_url,
            "source_instrument_url": href,
            "issuer_country_hint_iso2": country_hint,
            "meqiri_pea_listed": True,
            "eligibility_evidence": [],
            "exclusion_reason": None,
        })
    return rows


def main():
    fetched_at = datetime.now(timezone.utc).isoformat()
    discovered, errors = {}, []
    for region, url in SOURCES.items():
        try:
            html = fetch(url)
            rows = parse_meqiri_listing(html, url) if region == "meqiri" else parse_listing(html, region, url)
            if not rows:
                raise RuntimeError("No instrument rows parsed; source markup may have changed.")
            for row in rows:
                ticker = row.get("provisional_yahoo_ticker")
                key = ("ticker", ticker) if ticker else ("market", row["source_market"], row["source_code"], row["name"].casefold())
                current = discovered.get(key)
                if current is None:
                    row["source_regions"] = [region]
                    discovered[key] = row
                else:
                    current["source_regions"] = sorted(set(current.get("source_regions", [current["source_region"]]) + [region]))
                    if region == "meqiri":
                        current["meqiri_pea_listed"] = True
                        current["issuer_country_hint_iso2"] = row.get("issuer_country_hint_iso2")
                        current["pea_candidate_source_url"] = url
                        current["verification_status"] = "prequalified_pending_legal_review"
                        current["source_instrument_url"] = row.get("source_instrument_url") or current.get("source_instrument_url")
        except Exception as exc:
            errors.append({"region": region, "url": url, "error": str(exc)[:300]})
    if not discovered:
        print(json.dumps({"errors": errors}, ensure_ascii=False), file=sys.stderr)
        return 2
    document = {
        "schema_version": 1,
        "generated_at_utc": fetched_at,
        "source_count": len(SOURCES),
        "discovered_candidate_count": len(discovered),
        "verified_count": 0,
        "pending_verification_count": len(discovered),
        "provisional_ticker_mapped_count": sum(1 for row in discovered.values() if row["provisional_yahoo_ticker"]),
        "provisional_ticker_unmapped_count": sum(1 for row in discovered.values() if not row["provisional_yahoo_ticker"]),
        "meqiri_prequalified_count": sum(1 for row in discovered.values() if row.get("meqiri_pea_listed")),
        "important_notice": "Discovery only. Directory presence is not legal proof of PEA eligibility. All rows remain excluded from scoring until eligibility, instrument type, ISIN and tax conditions are independently verified.",
        "source_errors": errors,
        "candidates": sorted(discovered.values(), key=lambda x: (x["name"].casefold(), x["source_code"])),
    }
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Discovered {len(discovered)} candidates; 0 marked eligible; {len(errors)} source errors.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
