import unittest

from portfolio import optimize_mix


class PortfolioTests(unittest.TestCase):
    def test_optimizer_spends_budget_and_selects_metric_leader(self):
        games = [
            {"id": 1, "name": "A", "cost": 5, "chance_any_win_per_ticket": 0.25, "estimated_top_prize_probability": 0.001, "estimated_gross_ev": 3.0},
            {"id": 2, "name": "B", "cost": 10, "chance_any_win_per_ticket": 0.20, "estimated_top_prize_probability": 0.005, "estimated_gross_ev": 8.0},
        ]
        any_plan = optimize_mix(games, 20, "any_win")
        top_plan = optimize_mix(games, 20, "top_prize")
        value_plan = optimize_mix(games, 20, "expected_value")
        self.assertEqual(any_plan["items"], [{"id": 1, "name": "A", "count": 4, "cost": 20.0}])
        self.assertEqual(top_plan["items"], [{"id": 2, "name": "B", "count": 2, "cost": 20.0}])
        self.assertEqual(value_plan["items"], [{"id": 2, "name": "B", "count": 2, "cost": 20.0}])

    def test_optimizer_reports_unspent_remainder(self):
        games = [{"id": 1, "name": "A", "cost": 6, "chance_any_win_per_ticket": .2, "estimated_top_prize_probability": .001, "estimated_gross_ev": 4}]
        plan = optimize_mix(games, 20, "any_win")
        self.assertEqual(plan["spent"], 18)
        self.assertEqual(plan["unspent"], 2)


if __name__ == "__main__":
    unittest.main()
