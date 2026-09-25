import unittest

from data_source import extract_games


class ParserTests(unittest.TestCase):
    def test_extracts_embedded_all_games_json(self):
        html = """<script>WaLottery.Scratch.data = { all: JSON.parse('{\"Games\":[{\"Id\":9,\"GameName\":\"NINE\"}]}') };</script>"""
        games = extract_games(html)
        self.assertEqual(games, [{"Id": 9, "GameName": "NINE"}])

    def test_missing_payload_raises_clear_error(self):
        with self.assertRaisesRegex(ValueError, "embedded game data"):
            extract_games("<html></html>")


class FallbackSourceTests(unittest.TestCase):
    def test_uses_backup_page_when_explorer_fails(self):
        import data_source
        good = "all: JSON.parse('{\"Games\": [{\"Id\": 1}]}')"
        calls = []
        def fake(url, timeout):
            calls.append(url)
            if url == data_source.SOURCE_URL:
                raise OSError("explorer down")
            return good
        self.assertEqual(data_source.fetch_games(fetch_html=fake), [{"Id": 1}])
        self.assertEqual(calls, [data_source.SOURCE_URL, *data_source.FALLBACK_URLS])

    def test_reports_every_failed_source(self):
        import data_source
        with self.assertRaises(ValueError) as ctx:
            data_source.fetch_games(fetch_html=lambda url, timeout: "no data here")
        self.assertIn("explorer.aspx", str(ctx.exception))
        self.assertIn("/Scratch/", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
