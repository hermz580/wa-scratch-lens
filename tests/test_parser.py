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


if __name__ == "__main__":
    unittest.main()
