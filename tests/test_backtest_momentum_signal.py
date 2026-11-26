import unittest

from scripts.backtest_momentum_signal import percentile, rank_correlation, score_snapshot, summarize_observations


class MomentumBacktestTests(unittest.TestCase):
    def test_percentile_direction(self):
        values = [1.0, 2.0, 3.0]
        self.assertEqual(percentile(values, 3.0), 100.0)
        self.assertEqual(percentile(values, 3.0, lower_is_better=True), 0.0)

    def test_point_in_time_score_requires_minimum_coverage(self):
        cohort = {}
        for i in range(4):
            cohort[str(i)] = {
                "return_12_1m_pct": i * 5,
                "return_6m_pct": i * 4,
                "price_vs_sma200_pct": i * 3,
                "sma50_vs_sma200_pct": i * 2,
                "sharpe_3y": i * .2,
                "max_drawdown_1y_pct": -30 + i * 3,
                "volatility_1y_pct": 30 - i * 2,
                "relative_return_6m_pct": i * 2,
            }
        scores = score_snapshot(cohort)
        self.assertEqual(len(scores), 4)
        self.assertGreater(scores["3"], scores["0"])

    def test_rank_correlation_detects_positive_relationship(self):
        scores = {"A": 1.0, "B": 2.0, "C": 3.0, "D": 4.0}
        returns = {"A": -.1, "B": 0.0, "C": .1, "D": .2}
        self.assertAlmostEqual(rank_correlation(scores, returns), 1.0)

    def test_summary_reports_cost_adjusted_top_group_return(self):
        observations = [{
            "correlation": .5,
            "top2_avg_return": .10,
            "top2_avg_net_return": .089,
            "top2_positive_rate": 1.0,
            "spread": .08,
        }]
        summary = summarize_observations(observations)
        self.assertEqual(summary["snapshots"], 1)
        self.assertEqual(summary["top2_avg_return_pct"], 10.0)
        self.assertEqual(summary["top2_positive_rate_pct"], 100.0)


if __name__ == "__main__":
    unittest.main()
