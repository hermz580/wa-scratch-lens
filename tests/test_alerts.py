import tempfile
import unittest
from pathlib import Path

from alerts import compare_snapshots, save_snapshot


class AlertTests(unittest.TestCase):
    def test_initial_snapshot_does_not_create_change_alerts(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "snapshot.json"
            current = [{"id": 1, "name": "A", "top_prizes_remaining": 2, "return_rate": 0.7}]
            self.assertEqual(compare_snapshots(None, current), [])
            save_snapshot(path, current)
            self.assertTrue(path.exists())

    def test_reports_top_prize_drop_and_new_game(self):
        old = [{"id": 1, "name": "A", "top_prizes_remaining": 2, "return_rate": 0.7}]
        new = [
            {"id": 1, "name": "A", "top_prizes_remaining": 1, "return_rate": 0.7},
            {"id": 2, "name": "B", "top_prizes_remaining": 3, "return_rate": 0.8},
        ]
        alerts = compare_snapshots(old, new)
        kinds = {item["kind"] for item in alerts}
        self.assertEqual(kinds, {"top_prize_change", "new_game"})


if __name__ == "__main__":
    unittest.main()
