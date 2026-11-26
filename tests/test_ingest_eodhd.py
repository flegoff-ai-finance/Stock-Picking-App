import unittest
from datetime import datetime, timedelta, timezone

from scripts import ingest_eodhd as ingest


class IngestionMathTests(unittest.TestCase):
    def test_12_1_return_excludes_the_latest_month(self):
        latest = datetime(2026, 11, 25, tzinfo=timezone.utc)
        series = [
            (latest - timedelta(days=366), 100.0),
            (latest - timedelta(days=30), 120.0),
            (latest, 90.0),
        ]
        self.assertAlmostEqual(ingest.return_12_1(series), 20.0, places=6)

    def test_max_drawdown(self):
        latest = datetime(2026, 11, 25, tzinfo=timezone.utc)
        series = [(latest, 100.0), (latest + timedelta(days=1), 120.0), (latest + timedelta(days=2), 90.0)]
        self.assertAlmostEqual(ingest.max_drawdown(series), -25.0, places=6)

    def test_three_year_cagr(self):
        rows = [
            ("2022-12-31", {"totalRevenue": "100"}),
            ("2023-12-31", {"totalRevenue": "120"}),
            ("2024-12-31", {"totalRevenue": "144"}),
            ("2025-12-31", {"totalRevenue": "172.8"}),
        ]
        self.assertAlmostEqual(ingest.cagr(rows, ("totalRevenue",)), 20.0, places=6)

    def test_price_metrics_does_not_invent_sharpe_or_benchmark(self):
        latest = datetime(2026, 11, 25, tzinfo=timezone.utc)
        history = []
        for day in range(250):
            history.append({
                "date": (latest - timedelta(days=249-day)).date().isoformat(),
                "close": 100 + day * 0.1,
                "adjusted_close": 100 + day * 0.1,
            })
        result = ingest.price_metrics(history)
        self.assertIsNone(result["sharpe_3y"])
        self.assertIsNone(result["relative_return_6m_pct"])
        self.assertEqual(result["price_data_status"], "ok")

    def test_roic_remains_missing_without_tax_data(self):
        raw = {
            "Financials": {
                "Income_Statement": {"yearly": {
                    "2025-12-31": {"date": "2025-12-31", "totalRevenue": "100", "operatingIncome": "20", "ebitda": "25"}
                }},
                "Balance_Sheet": {"yearly": {
                    "2025-12-31": {"date": "2025-12-31", "shortLongTermDebtTotal": "10", "cashAndCashEquivalents": "5", "totalStockholderEquity": "50"}
                }},
            }
        }
        result = ingest.fundamental_metrics(raw)
        self.assertIsNone(result["roic_pct"])


if __name__ == "__main__":
    unittest.main()
