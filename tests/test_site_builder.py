import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import site_builder


def raw_game(game_id, top_rem=2, rem=400, cost=5):
    return {"Id": game_id, "GameName": f"GAME {game_id}", "Cost": cost, "OverallOdds": "1 in 4.00",
            "LastUpdated": "9/25/2026 12:35:05 AM",
            "Prizes": [{"PrizeAmount": "$1000", "TotalPrizesNumber": 2, "PrizesRemainingNumber": top_rem},
                       {"PrizeAmount": "$10", "TotalPrizesNumber": 500, "PrizesRemainingNumber": rem}]}


NOW = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)


class SiteBuilderTests(unittest.TestCase):
    def test_first_build_is_a_baseline_without_new_game_events(self):
        latest, history = site_builder.build([raw_game(1), raw_game(2)], None, NOW)
        self.assertEqual(latest["game_count"], 2)
        self.assertEqual(latest["events"], [])
        self.assertIsNone(history["games"]["1"]["first_seen"])
        self.assertEqual([g["rank"] for g in latest["games"]], [1, 2])

    def test_new_claimed_and_retired_games_create_events(self):
        _, history = site_builder.build([raw_game(1), raw_game(2)], None, NOW)
        later = NOW + timedelta(days=1)
        latest, history = site_builder.build([raw_game(1, top_rem=1), raw_game(3)], history, later)
        kinds = {e["kind"]: e for e in latest["events"]}
        self.assertEqual(set(kinds), {"new_game", "top_claimed", "retired"})
        new = next(g for g in latest["games"] if g["id"] == 3)
        self.assertTrue(new["is_new"])
        self.assertEqual(history["games"]["3"]["first_seen"], later.isoformat(timespec="seconds"))
        self.assertIsNotNone(history["games"]["2"]["retired_at"])

    def test_games_stop_being_new_after_window(self):
        _, history = site_builder.build([raw_game(1)], None, NOW)
        _, history = site_builder.build([raw_game(1), raw_game(3, rem=100)], history, NOW + timedelta(days=1))
        latest, _ = site_builder.build([raw_game(1), raw_game(3, rem=100)], history, NOW + timedelta(days=40))
        self.assertFalse(next(g for g in latest["games"] if g["id"] == 3)["is_new"])

    def test_trend_uses_daily_points(self):
        _, history = site_builder.build([raw_game(1, rem=400)], None, NOW)
        latest, _ = site_builder.build([raw_game(1, rem=300)], history, NOW + timedelta(days=10))
        self.assertEqual(latest["games"][0]["tickets_per_day"], 40)

    def test_run_writes_only_when_data_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            self.assertTrue(site_builder.run(data_dir, fetcher=lambda: [raw_game(1)], now=NOW))
            self.assertFalse(site_builder.run(data_dir, fetcher=lambda: [raw_game(1)], now=NOW))
            self.assertTrue(site_builder.run(data_dir, fetcher=lambda: [raw_game(1, rem=399)], now=NOW))
            latest = json.loads((data_dir / "latest.json").read_text())
            self.assertEqual(latest["check_minutes"], site_builder.CHECK_MINUTES)

    def test_run_rejects_empty_feed(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
            site_builder.run(Path(tmp), fetcher=lambda: [], now=NOW)


if __name__ == "__main__":
    unittest.main()
