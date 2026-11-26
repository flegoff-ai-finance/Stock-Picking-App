import importlib.util
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "build_discovery_universe.py"
spec = importlib.util.spec_from_file_location("discovery", MODULE)
discovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(discovery)


def test_valid_isin_checksum():
    assert discovery.valid_isin("NL0010273215")
    assert not discovery.valid_isin("NL0010273216")


def test_filters_and_deduplicates_by_isin():
    rows = {
        "PAR": [
            {"symbol": "AAA.PA", "name": "Alpha", "isin": "FR0000062465",
             "country": "France", "delisted": "False", "market": "Euronext Paris"},
            {"symbol": "OLD.PA", "name": "Old", "isin": "FR0000062465",
             "country": "France", "delisted": "True"},
            {"symbol": "US.PA", "name": "US issuer", "isin": "US0378331005",
             "country": "United States", "delisted": "False"},
            {"symbol": "NOIS.PA", "name": "No ISIN", "isin": "",
             "country": "France", "delisted": "False"},
        ],
        "AMS": [
            {"symbol": "AAA.AS", "name": "Alpha NV", "isin": "FR0000062465",
             "country": "France", "delisted": "False", "market": "Euronext Amsterdam"},
        ],
    }
    result = discovery.build_candidates(rows, "abc123", "2026-11-26T00:00:00+00:00")
    assert len(result) == 1
    assert result[0]["ticker"] == "AAA.PA"
    assert result[0]["discovery_status"] == "unverified_pea"
