# European discovery universe

## Purpose
This is a discovery feed for finding companies worth researching. It is not a PEA-eligibility register. Once financial metrics are ingested into `data/discovery_financials.json`, it feeds the hidden first screening layer; the separate PEA register is applied only in layer 2. Unverified candidates never reach the strategy engines or virtual portfolios.

## Source
The feed is built from the public FinanceDatabase repository, using the exchange-specific equity CSV files for Paris, Amsterdam, Brussels, Milan, Xetra, Stockholm, Copenhagen, Helsinki, Oslo, Lisbon, Vienna, Athens, Prague, Budapest, Warsaw, Frankfurt, Hamburg, Munich and Berlin. The upstream repository is MIT-licensed; its README describes the dataset as aggregated from public exchange directories and other public reference sources. Source attribution, commit SHA and retrieval timestamp are retained on each row.

## Filters and limitations
- Only rows with a valid ISIN checksum, a recognized EU/EEA issuer country, a name and a ticker are retained.
- Delisted rows are excluded.
- Duplicate ISINs are collapsed, preferring the first market in the configured market priority.
- The upstream country, instrument classification and ticker mapping can contain errors. In particular, a listing venue or ticker suffix does not prove issuer domicile, ordinary-share status, Yahoo ticker validity or PEA eligibility.
- No candidate is promoted automatically. All rows carry `discovery_status=unverified_pea`.

## Promotion gate
To enter the scoring universe, a candidate must separately pass the evidence process in `data/pea_verification.csv`: exact ISIN/ticker mapping, EU/EEA registered office, corporate tax condition, ordinary-share classification, independent PEA-eligibility evidence, issuer source, reviewer and verification date. The existing 90-day freshness rule remains in force.

## Refresh
GitHub Actions refreshes the metadata discovery feed weekly and on manual dispatch. The workflow never writes to `pea_verification.csv` or `technical_screener.json`. Financial enrichment is a separate pipeline and has not yet been completed; the application falls back to the seven verified pilot securities while `data/discovery_financials.json` is absent.
