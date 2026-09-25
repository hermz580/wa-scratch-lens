import unittest

from smart_score import game_metrics, prize_value, score, trend


def raw_game(tiers, cost=10, odds="1 in 4.00", game_id=1):
    return {"Id": game_id, "GameName": "TEST &amp; GAME", "Cost": cost, "OverallOdds": odds,
            "Prizes": [{"PrizeAmount": label, "TotalPrizesNumber": total, "PrizesRemainingNumber": rem}
                       for label, total, rem in tiers]}


class SmartScoreTests(unittest.TestCase):
    def test_prize_value_parses_cash_annuity_and_non_cash(self):
        self.assertEqual(prize_value("$1,000"), (1000.0, False))
        self.assertEqual(prize_value("$40,000/yr/25 years"), (1_000_000.0, True))
        self.assertEqual(prize_value("BRONCO"), (None, False))

    def test_untouched_game_has_equal_launch_and_current_return(self):
        m = game_metrics(raw_game([("$1000", 2, 2), ("$20", 100, 100), ("$10", 500, 500)]))
        self.assertAlmostEqual(m["rtp"], m["launch_rtp"])
        self.assertAlmostEqual(m["richness"], 1.0)
        self.assertEqual(m["name"], "TEST & GAME")
        self.assertAlmostEqual(m["sold_pct"], 0.0)

    def test_big_prizes_outlasting_small_ones_raises_drift_and_score(self):
        fresh = score(game_metrics(raw_game([("$1000", 2, 2), ("$20", 100, 100), ("$10", 500, 500)])))
        rich = score(game_metrics(raw_game([("$1000", 2, 2), ("$20", 100, 50), ("$10", 500, 150)])))
        drained = score(game_metrics(raw_game([("$1000", 2, 0), ("$20", 100, 50), ("$10", 500, 150)])))
        self.assertGreater(rich["drift"], 0)
        self.assertGreater(rich["score"], fresh["score"])
        self.assertLess(drained["score"], fresh["score"])
        self.assertEqual(drained["verdict"], "skip")
        self.assertTrue(any("top prize is gone" in r for r in drained["reasons"]))

    def test_non_cash_prize_marks_return_as_floor(self):
        m = score(game_metrics(raw_game([("TRUCK", 1, 1), ("$20", 100, 100)])))
        self.assertTrue(m["rtp_is_floor"])
        self.assertIn("at least", m["reasons"][0])
        self.assertIsNone(m["top_value"])

    def test_score_bounds(self):
        m = score(game_metrics(raw_game([("$1000000", 1, 1), ("$5", 10, 1)], odds="1 in 1.00")))
        self.assertLessEqual(m["score"], 100)
        self.assertGreaterEqual(m["score"], 0)

    def test_trend_estimates_days_left(self):
        points = [{"t": "2026-09-01", "rw": 1000}, {"t": "2026-09-11", "rw": 900}]
        self.assertEqual(trend(points, odds=4.0, est_remaining=3600), {"tickets_per_day": 40, "days_left": 90})
        self.assertEqual(trend(points[:1], 4.0, 3600)["days_left"], None)


if __name__ == "__main__":
    unittest.main()
