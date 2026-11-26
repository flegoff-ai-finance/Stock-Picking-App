# Market data pipeline

## Provider pilot: EOD Historical Data (EODHD)

The ingestion job reads the existing `data/technical_screener.json` registry and updates only instruments whose PEA status is already verified in that registry. It does **not** discover securities or determine PEA eligibility.

### Activate

1. First validate that the required endpoints cover the target exchanges and small caps. The current EODHD personal free package does not include company fundamentals and only includes one year of EOD prices; this pipeline needs the paid combination of EOD history and fundamentals (the published All-In-One plan is $99.99/month on monthly billing).
2. Do not subscribe until the coverage test is satisfactory and the cost is explicitly accepted.
3. If approved, create an EODHD account, obtain an API token, and add a GitHub Actions repository secret named `EODHD_API_TOKEN`.
4. Run **Actions → Refresh market and fundamental data → Run workflow**.

The workflow also runs on weekdays at 06:25 UTC once the secret exists. No API key is stored in source code.

### Important data limitations

- The current registry still contains only the seven pilot securities; this is not the complete PEA universe.
- The script requests up to three years of EOD prices and the EODHD fundamentals payload.
- It computes 6-month and 12-month returns, 12-1 momentum, moving-average distances, volatility, and drawdowns.
- It extracts annual revenue/operating-income growth, operating margin, FCF margin, ROIC, net debt/EBITDA and forward P/E where source fields are present.
- EODHD's next-year EPS growth estimate is stored separately. It is **not** substituted for the classic 3–5 year growth input of the PEG engine.
- Sharpe is left null until a dated EUR risk-free series is connected. Relative momentum is left null until a verified benchmark ticker is mapped for each instrument.
- All missing fields remain null. The scoring engines therefore keep a stock unranked when required inputs are absent.

## Provider cost and license gate

EODHD pricing and package coverage were checked on 26 November 2026. The published personal All-In-One offer combines global end-of-day prices and fundamentals at $99.99/month; the free package does not provide the fundamentals feed required by the Quality engine. No subscription has been purchased and the workflow remains inactive until the repository secret is configured. Confirm data-display rights and personal-use restrictions before redistributing provider data in a public application.

## Next validation gates

1. Validate EODHD ticker mapping and field coverage across a representative sample of EU/EEA markets and small caps.
2. Validate company/ISIN/tax-residence criteria for the complete PEA-eligible universe independently of market-data coverage.
3. Add a provider for 3–5 year EPS consensus estimates if EODHD does not provide adequate coverage.
4. Add benchmark mappings and EUR risk-free data before activating the Sharpe and relative-momentum components.

This pipeline is for research and virtual portfolio simulation only. It does not submit orders.
