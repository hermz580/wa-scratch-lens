import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]


class FrontendTests(unittest.TestCase):
    def test_dashboard_has_budget_controls_three_rankings_alerts_and_disclaimer(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        for marker in ["budget", "best-any", "best-ev", "best-top", "prize-board", "prize-game", "prize-tier-rows", "agent-operations", "operations-grid", "audit-trail", "jackpot-watch", "strategy-plans", "probability-lab", "alerts", "1-800-547-6133"]:
            self.assertIn(marker, html)

    def test_script_fetches_live_api_and_supports_all_rankings(self):
        script = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        for marker in ["/api/games?budget=", "prize_tiers", "prize-game", "operations", "quality", "run_id", "jackpot_watchlist", "top_prize_one_in", "spend_for_1pct_top_prize", "spend_for_5pct_top_prize", "spend_for_50pct_top_prize", "chance_any_win", "chance_no_prize", "chance_exactly_one_prize", "chance_two_or_more_prizes", "estimated_budget_return", "plans", "return_rate", "chance_top_prize", "alerts-enabled", "setInterval"]:
            self.assertIn(marker, script)


if __name__ == "__main__":
    unittest.main()
