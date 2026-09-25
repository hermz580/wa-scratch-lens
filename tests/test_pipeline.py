import unittest

from agent_pipeline import AgentPipeline


def sample_games():
    return [{
        "Id": 1, "GameName": "TEST", "Cost": 5, "OverallOdds": "1 in 4.00",
        "TicketsPrinted": "400", "LastUpdated": "2026-09-25",
        "GridImageUrl": "", "Prizes": [
            {"PrizeAmount": "$100", "TotalPrizesNumber": 10, "PrizesRemainingNumber": 5},
            {"PrizeAmount": "$5", "TotalPrizesNumber": 90, "PrizesRemainingNumber": 45},
        ]
    }]


class PipelineTests(unittest.TestCase):
    def test_real_workers_publish_only_after_quality_gate(self):
        pipeline = AgentPipeline(fetcher=sample_games)
        result = pipeline.run(20)
        self.assertEqual(result["quality"]["verdict"], "publish")
        self.assertEqual(result["games"][0]["name"], "TEST")
        agents = {a["id"]: a for a in result["operations"]["agents"]}
        for worker in ["source-scout", "game-analyst", "portfolio-planner", "jackpot-sentinel", "quality-gate"]:
            self.assertEqual(agents[worker]["status"], "healthy")
            self.assertIsNotNone(agents[worker]["duration_ms"])
        self.assertGreaterEqual(len(result["operations"]["events"]), 5)

    def test_malformed_game_is_quarantined_and_publication_is_degraded(self):
        bad = sample_games() + [{"Id": 2, "GameName": "BROKEN", "Cost": 1, "OverallOdds": "bad", "Prizes": []}]
        pipeline = AgentPipeline(fetcher=lambda: bad)
        result = pipeline.run(20)
        self.assertEqual(result["quality"]["verdict"], "publish_degraded")
        self.assertEqual(len(result["errors"]), 1)
        analyst = next(a for a in result["operations"]["agents"] if a["id"] == "game-analyst")
        self.assertEqual(analyst["status"], "degraded")
        self.assertEqual(analyst["records_failed"], 1)


if __name__ == "__main__":
    unittest.main()
