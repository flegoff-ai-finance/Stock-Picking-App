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


def main():
    fetched_at = datetime.now(timezone.utc).isoformat()
    discovered, errors = {}, []
    for region, url in SOURCES.items():
        try:
            rows = parse_listing(fetch(url), region, url)
            if not rows:
                raise RuntimeError("No instrument rows parsed; source markup may have changed.")
            for row in rows:
                key = (row["source_market"], row["source_code"], row["name"].casefold())
                current = discovered.get(key)
                if current is None:
                    discovered[key] = row
                else:
                    current["source_regions"] = sorted(set(current.get("source_regions", [current["source_region"]]) + [region]))
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
