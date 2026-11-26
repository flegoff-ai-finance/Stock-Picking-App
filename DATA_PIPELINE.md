# Market data pipeline

## Source strategy

Yahoo Finance is the preferred first source for the personal research prototype, using the community-maintained Python package `yfinance`. It can provide historical prices and selected company fundamentals / estimates without a paid API key. Coverage and field quality vary by exchange and security, especially for smaller European companies.

Other sources to validate or cross-check selectively:
- Google Finance / Google Sheets: supplementary price checks; not a full fundamentals feed.
- ABC Bourse: useful French-market histories and selected ratios; automated access and terms must be checked.
- Zonebourse: useful for financial statements, estimates and analyst consensus; some datasets and automated access may be restricted or paid.
- Issuer annual reports and investor-relations publications remain the preferred source for audited financial statement data.

Before automating collection or redistributing any provider data in a public website, verify the provider's terms, licensing and permitted use. Free to view does not automatically mean free to scrape, automate or republish.

## Current implementation status

- The application now has a three-layer selection engine documented in `SELECTION_METHODOLOGY.md`.
- The current registry `data/technical_screener.json` still contains seven pilot securities only. It is not the complete PEA universe.
- The PEA status gate remains independent from market-data providers. A data vendor listing does not prove PEA eligibility.
- The previous EODHD ingestion script remains in the repository as a dormant alternative. No subscription has been purchased and no API token is configured.
- `scripts/ingest_yahoo.py` is the first Yahoo Finance adapter. It refreshes only the already verified registry entries, retrieves up to three years of adjusted daily prices, and attempts selected annual financial fields.\n- The Yahoo connector workflow runs on weekdays at 06:25 UTC and can also be started manually. It installs `yfinance` in the runner; no API key or paid subscription is required.\n- Yahoo `earningsGrowth` is deliberately not treated as a forward EPS growth estimate. The next-year and 3–5 year EPS growth fields remain N/D until a correctly defined estimate field is validated.\n- The connector has been added but live Yahoo retrieval and the first GitHub Actions run still need confirmation. The current registry remains seven pilot securities.

## Yahoo Finance pilot — intended scope

Use `yfinance` for:
- adjusted daily price history (where available) to calculate returns, moving averages, volatility and drawdowns;
- selected annual financial statements to calculate revenue growth, operating margins and free-cash-flow margins;
- forward P/E and available near-term analyst estimates, with explicit field-level availability checks.

Do not assume Yahoo supplies a reliable 3–5 year EPS growth consensus for every European stock. The classic PEG remains N/D when that specific input is absent. A one-year estimate can be used in the broad first screening layer only; it must not be substituted into the PEG calculation.

## Data quality rules

- Every metric must carry a provider, retrieval timestamp and underlying observation date where possible.
- Keep missing values null. Never fabricate a value, infer PEA eligibility from an exchange, or silently substitute a different forecast horizon.
- Record provider errors per security without stopping the full batch.
- Keep price history, fundamental statements, analyst estimates and PEA eligibility as distinct data domains.
- Preserve excluded securities and exclusion reasons to reduce survivorship bias.
- Show coverage and freshness alongside every ranking.
- Reconcile key company financials with issuer-published reports before relying on them for final decisions.

## Previous EODHD option (dormant)

The EODHD script and manual GitHub Actions workflow are retained only as a possible fallback. The published All-in-One plan was previously identified at $99.99/month on monthly billing. Do not subscribe unless Yahoo coverage proves inadequate, a representative comparison demonstrates material value, and the cost is explicitly approved.

This application is for research and virtual portfolio simulation only. It does not submit orders.


## Analyst growth estimates and EUR risk-free rate

The Yahoo ingestion also requests `get_growth_estimates(as_dict=True)`:
- `+1y` populates the next-year EPS growth context field.
- `+5y` populates the annualized five-year EPS growth field used by the classic PEG.
- Missing Yahoo consensus values remain null; the generic `earningsGrowth` field is not substituted.

For Sharpe, the pipeline downloads the ECB daily €STR series `EST.B.EU000A2X2A25.WT`, aligns the last known daily rate to each stock return date, converts the annualized percentage using ACT/360, and annualizes excess-return Sharpe with sqrt(252). If the ECB series is unavailable or coverage is insufficient, Sharpe remains null and the source error is recorded.

Official series: https://data.ecb.europa.eu/data/datasets/EST/EST.B.EU000A2X2A25.WT
