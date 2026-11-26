import unittest
from datetime import date, timedelta
from scripts.ingest_yahoo import (cagr, calculate_relative_return, calculate_sharpe, growth_estimate_value, parse_estr_csv, price_metrics, select_ingestion_batch, verified_instruments)


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

    def test_relative_return_uses_same_six_month_window(self):
        stock = [(date(2025, 12, 30), 100.0), (date(2026, 7, 1), 120.0)]
        benchmark = [(date(2025, 12, 30), 100.0), (date(2026, 7, 1), 110.0)]
        self.assertAlmostEqual(calculate_relative_return(stock, benchmark), 10.0, places=6)

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

    def test_ingestion_batch_prioritizes_missing_and_old_data(self):
        rows = [
            {"ticker": "NEW.PA"},
            {"ticker": "OLD.PA", "market_data_last_updated_utc": "2026-01-01T00:00:00+00:00"},
            {"ticker": "FRESH.PA", "market_data_last_updated_utc": "2026-11-25T00:00:00+00:00"},
        ]
        selected = select_ingestion_batch(rows, 2)
        self.assertEqual([row["ticker"] for row in selected], ["NEW.PA", "OLD.PA"])

    def test_empty_history_is_explicit(self):
        class Empty:
            empty = True
        self.assertEqual(price_metrics(Empty())["price_data_status"], "missing_history")


if __name__ == "__main__":
    unittest.main()
