import math
import unittest

from analytics import analyze_game, affordable_tickets, probability_at_least_one, tickets_for_target_probability


class AnalyticsTests(unittest.TestCase):
    def test_budget_probability_uses_affordable_ticket_count(self):
        self.assertEqual(affordable_tickets(25, 10), 2)
        self.assertAlmostEqual(probability_at_least_one(0.25, 2), 0.4375)

    def test_target_probability_reports_required_tickets(self):
        self.assertEqual(tickets_for_target_probability(0.01, 0.50), 69)
        self.assertEqual(tickets_for_target_probability(0.0, 0.50), 0)

    def test_analyze_game_reports_any_win_and_top_prize_probabilities(self):
        game = {
            "Id": 1,
            "GameName": "TEST GAME",
            "Cost": 5,
            "OverallOdds": "1 in 4.00",
            "TicketsPrinted": "400",
            "LastUpdated": "2026-09-25",
            "Prizes": [
                {"PrizeAmount": "$100", "TotalPrizesNumber": 10, "PrizesRemainingNumber": 5},
                {"PrizeAmount": "$5", "TotalPrizesNumber": 90, "PrizesRemainingNumber": 45},
            ],
        }
        result = analyze_game(game, 20)
        self.assertEqual(result["tickets_affordable"], 4)
        self.assertAlmostEqual(result["chance_any_win"], 1 - 0.75**4)
        self.assertAlmostEqual(result["estimated_top_prize_probability"], 5 / 200)
        self.assertAlmostEqual(result["chance_top_prize"], 1 - (1 - 5/200)**4)
        self.assertEqual(result["top_prizes_remaining"], 5)
        self.assertAlmostEqual(result["chance_no_prize"], 0.75**4)
        self.assertAlmostEqual(result["chance_exactly_one_prize"], 4 * 0.25 * 0.75**3)
        self.assertAlmostEqual(result["chance_two_or_more_prizes"], 1 - 0.75**4 - (4 * 0.25 * 0.75**3))
        self.assertAlmostEqual(result["expected_winning_tickets"], 1.0)
        self.assertAlmostEqual(result["estimated_budget_return"], result["estimated_gross_ev"] * 4)
        self.assertAlmostEqual(result["estimated_budget_net"], result["estimated_budget_return"] - 20)
        self.assertGreater(result["payout_standard_deviation"], 0)
        self.assertEqual(result["top_prize_one_in"], 40)
        self.assertEqual(result["top_prize_expected_spend"], 200)
        self.assertGreater(result["spend_for_50pct_top_prize"], 100)
        self.assertEqual(len(result["prize_tiers"]), 2)
        self.assertEqual(result["prize_tiers"][0]["total"], 10)
        self.assertEqual(result["prize_tiers"][0]["remaining"], 5)
        self.assertEqual(result["prize_tiers"][0]["paid"], 5)
        self.assertAlmostEqual(result["prize_tiers"][0]["estimated_one_in"], 40)
        self.assertAlmostEqual(result["prize_tiers"][0]["chance_with_budget"], 1 - (1 - 1/40)**4)

    def test_unknown_non_cash_prize_makes_expected_value_unavailable(self):
        game = {
            "Id": 2,
            "GameName": "CAR GAME",
            "Cost": 10,
            "OverallOdds": "1 in 3.00",
            "TicketsPrinted": "300",
            "Prizes": [
                {"PrizeAmount": "BRONCO", "TotalPrizesNumber": 1, "PrizesRemainingNumber": 1},
                {"PrizeAmount": "$10", "TotalPrizesNumber": 99, "PrizesRemainingNumber": 99},
            ],
        }
        result = analyze_game(game, 30)
        self.assertIsNone(result["estimated_gross_ev"])
        self.assertFalse(result["ev_complete"])
        self.assertIn("BRONCO", result["unknown_prize_labels"])

    def test_zero_top_prizes_returns_zero_probability(self):
        game = {
            "Id": 3,
            "GameName": "DEPLETED",
            "Cost": 2,
            "OverallOdds": "1 in 4.00",
            "TicketsPrinted": "400",
            "Prizes": [
                {"PrizeAmount": "$100", "TotalPrizesNumber": 10, "PrizesRemainingNumber": 0},
                {"PrizeAmount": "$2", "TotalPrizesNumber": 90, "PrizesRemainingNumber": 45},
            ],
        }
        result = analyze_game(game, 10)
        self.assertEqual(result["estimated_top_prize_probability"], 0)
        self.assertEqual(result["chance_top_prize"], 0)


if __name__ == "__main__":
    unittest.main()
