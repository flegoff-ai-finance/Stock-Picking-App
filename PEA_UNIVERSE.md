# PEA candidate discovery and eligibility controls

The discovery job imports instrument names and trading codes from ProRealTime's public France, Europe and EEA PEA directories. It is a **candidate source only**, not a legal eligibility certificate.

Every discovered record is created with:
- `pea_status=pending_verification`
- `verification_status=not_verified`
- no ISIN unless separately obtained and validated
- no inclusion in the scoring universe

A candidate may be moved into the scored universe only after a separate review confirms:
1. the instrument is an eligible ordinary share (not a preference share, SIIC, warrant, right, bond, etc.);
2. the issuer's registered office is in the EU/EEA;
3. the issuer is subject to the relevant corporate income tax or equivalent regime;
4. the ISIN and the exact listed share class are confirmed;
5. the source and date of each check are recorded.

The official French tax doctrine and AMF/Service-Public guidance govern the legal criteria. A directory label alone does not override them. The discovery job must never change `pea_status` to `eligible`.

Yahoo tickers inferred from exchange codes are provisional mapping hints only. They are not used by the market-data ingestion pipeline until a verified ISIN, ticker and PEA evidence record are available.

This separation prevents false positives from entering the 150-candidate screens and keeps unverified securities visible for later review without affecting scores.
