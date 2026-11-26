import unittest
from datetime import date
from scripts.ingest_yahoo import cagr, price_metrics, verified_instruments


class YahooIngestionTests(unittest.TestCase):
    def test_cagr_three_years(self):
        self.assertAlmostEqual(cagr([172.8, 144, 120, 100]), 20.0)

    def test_cagr_requires_positive_complete_history(self):
        self.assertIsNone(cagr([100, 90, 80]))
        self.assertIsNone(cagr([100, 90, 80, 0]))

    def test_verified_universe_does_not_promote_unchecked(self):
        doc = {"instruments": [
            {"ticker": "AAA.PA", "isin": "FR0000000001", "pea_status": "eligible", "pea_checked_at": "2026-11-20"},
            {"ticker": "BBB.PA", "isin": "FR0000000002", "pea_status": "unknown", "pea_checked_at": "2026-11-20"},
            {"ticker": "CCC.PA", "isin": "FR0000000003", "pea_status": "eligible", "pea_checked_at": "2026-01-01"},
        ]}
        self.assertEqual(len(verified_instruments(doc, date(2026, 11, 26))), 1)

    def test_empty_history_is_explicit(self):
        class Empty:
            empty = True
        self.assertEqual(price_metrics(Empty())["price_data_status"], "missing_history")


if __name__ == "__main__":
    unittest.main()
