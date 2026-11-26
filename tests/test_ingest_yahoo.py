import unittest
from datetime import date, timedelta
from scripts.ingest_yahoo import (cagr, calculate_sharpe, growth_estimate_value, parse_estr_csv, price_metrics, verified_instruments)


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

    def test_growth_estimates_use_explicit_yahoo_horizons(self):
        estimates = {"stock": {"+1y": 0.125, "+5y": 0.18}}
        self.assertAlmostEqual(growth_estimate_value(estimates, "+1y"), 12.5)
        self.assertAlmostEqual(growth_estimate_value(estimates, "+5y"), 18.0)
        self.assertIsNone(growth_estimate_value(estimates, "+3y"))

    def test_ecb_estr_csv_parser(self):
        content = """TIME_PERIOD,OBS_VALUE
2026-11-24,2.105
2026-11-25,2.104
"""
        rates = parse_estr_csv(content)
        self.assertEqual(rates[date(2026, 11, 24)], 2.105)
        self.assertEqual(len(rates), 2)

    def test_sharpe_uses_aligned_risk_free_rate(self):
        start = date(2025, 1, 1)
        points = []
        rates = {}
        price = 100.0
        for i in range(260):
            day = start + timedelta(days=i)
            points.append((day, price))
            rates[day] = 2.0
            price *= 1.001 if i % 2 else 1.003
        value = calculate_sharpe(points, rates)
        self.assertIsNotNone(value)
        self.assertGreater(value, 0)

    def test_empty_history_is_explicit(self):
        class Empty:
            empty = True
        self.assertEqual(price_metrics(Empty())["price_data_status"], "missing_history")


if __name__ == "__main__":
    unittest.main()
