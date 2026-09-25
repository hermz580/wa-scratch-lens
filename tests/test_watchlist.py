import unittest

from watchlist import build_jackpot_watchlist


class WatchlistTests(unittest.TestCase):
    def test_ranks_all_open_games_by_highest_top_prize(self):
        games = [
            {"id": 1, "name": "SMALL", "cost": 2, "top_prize_label": "$1,000", "top_prizes_remaining": 4, "top_prize_one_in": 1000, "top_prize_expected_spend": 2000, "spend_for_1pct_top_prize": 22, "spend_for_5pct_top_prize": 106, "spend_for_50pct_top_prize": 1386},
            {"id": 2, "name": "BIG", "cost": 20, "top_prize_label": "$1,000,000", "top_prizes_remaining": 1, "top_prize_one_in": 500000, "top_prize_expected_spend": 10000000, "spend_for_1pct_top_prize": 100520, "spend_for_5pct_top_prize": 512940, "spend_for_50pct_top_prize": 6931480},
            {"id": 3, "name": "GONE", "cost": 10, "top_prize_label": "$2,000,000", "top_prizes_remaining": 0, "top_prize_one_in": None, "top_prize_expected_spend": None, "spend_for_1pct_top_prize": None, "spend_for_5pct_top_prize": None, "spend_for_50pct_top_prize": None},
        ]
        result = build_jackpot_watchlist(games)
        self.assertEqual([g["name"] for g in result], ["BIG", "SMALL"])
        self.assertEqual(result[0]["minimum_entry_spend"], 20)


if __name__ == "__main__":
    unittest.main()
