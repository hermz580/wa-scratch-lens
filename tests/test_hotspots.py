import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import hotspots

NOW = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)


def loc(num, city="SEATTLE", amount=1000.0, name=None):
    return {"Number": str(num), "Name": name or f"STORE {num}", "Address": "1 MAIN ST", "City": city,
            "Lattitude": "47.6", "Longitude": "-122.3", "WinningAmount": amount}


def page(locations):
    data = json.dumps({"Locations": locations, "Result": None}).replace("'", "\\'")
    return f"<script>WaLottery.WinningHotspots.mapData = JSON.parse('{data}');</script>"


class HotspotTests(unittest.TestCase):
    def test_extracts_stores_and_skips_malformed(self):
        stores = hotspots.extract_hotspots(page([loc(1, name="JOE'S MART"), {"Number": "2"}]))
        self.assertEqual(len(stores), 1)
        self.assertEqual(stores[0]["name"], "JOE'S MART")
        self.assertEqual(stores[0]["city"], "Seattle")

    def test_missing_data_raises(self):
        with self.assertRaises(ValueError):
            hotspots.extract_hotspots("<html></html>")

    def test_baseline_then_new_store_and_repeat_win(self):
        first = hotspots.extract_hotspots(page([loc(1), loc(2, city="TACOMA")]))
        payload, hist = hotspots.build(first, None, NOW)
        self.assertEqual(payload["events"], [])
        self.assertFalse(any(s["is_new"] for s in payload["stores"]))

        later = NOW + timedelta(days=1)
        second = hotspots.extract_hotspots(page([loc(1, amount=5000.0), loc(2, city="TACOMA"), loc(3)]))
        payload, hist = hotspots.build(second, hist, later)
        by_id = {s["id"]: s for s in payload["stores"]}
        self.assertEqual(by_id["1"]["wins"], 2)
        self.assertTrue(by_id["3"]["is_new"])
        self.assertEqual(len(payload["events"]), 2)
        self.assertEqual(payload["cities"][0]["city"], "Seattle")
        self.assertEqual(payload["cities"][0]["wins"], 3)

    def test_run_skips_write_when_unchanged(self):
        stores = hotspots.extract_hotspots(page([loc(1)]))
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(hotspots.run(Path(d), fetcher=lambda: stores, now=NOW))
            self.assertFalse(hotspots.run(Path(d), fetcher=lambda: stores, now=NOW))


if __name__ == "__main__":
    unittest.main()
