# PEA universe governance

## Current state

The scored universe contains seven verified pilot securities. No larger universe is currently imported.

Automated collection from ProRealTime and MEQIRI has been removed after reviewing their published terms:
- ProRealTime's terms prohibit extraction or reuse of its databases.
- MEQIRI's terms prohibit automated retrieval, copying and publication of its content at scale.

Those sources must not be used by the application's automated workflows. Individual pages may be consulted manually for a one-off research question, subject to their terms, but their lists and data must not be scraped or bulk-copied.

## Approved path to expand the universe

The application accepts candidates from a broker export or a data provider whose licence permits the intended use. The import template is `data/pea_verification.csv`.

Each candidate must include:
1. a unique candidate ID and company name;
2. the exact ISIN and Yahoo ticker mapping;
3. issuer registered-office country in the EU/EEA;
4. confirmation that the issuer is subject to corporate income tax or an equivalent regime;
5. confirmation that the instrument is an ordinary share;
6. a source documenting PEA eligibility and a separate issuer source;
7. reviewer and verification date.

`scripts/build_pea_registry.py` rejects incomplete, stale (over 90 days), duplicate or inconsistent reviews. A provisional ticker or a third-party directory label alone never promotes a security to eligible. `scripts/sync_pea_registry.py` adds only approved rows to the technical universe, after which Yahoo enrichment processes up to 50 oldest/missing securities per run.

## Scoring gate

Only securities with `pea_status=eligible`, a valid ISIN, a ticker and a recent verification date can enter the technical scoring universe. Unverified candidates remain outside all three strategy engines and virtual portfolios.

## Data licensing

Yahoo Finance is accessed through the unofficial `yfinance` client for the current personal-use pilot. Usage terms and redistribution rights must be confirmed before broad public deployment. The app must not publish third-party data beyond the permissions granted by its provider.
