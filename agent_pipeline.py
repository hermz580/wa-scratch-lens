from __future__ import annotations

import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from alerts import compare_snapshots
from analytics import analyze_game
from data_source import SOURCE_URL, fetch_games
from portfolio import optimize_mix
from watchlist import build_jackpot_watchlist


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class AgentPipeline:
    """Supervised worker pipeline with independent jobs and telemetry."""

    def __init__(self, fetcher=fetch_games):
        self.fetcher = fetcher
        self.run_id = None
        self.agents = {}
        self.events = []

    def _worker(self, worker_id, responsibility, fn, records_in=0):
        started = time.perf_counter()
        started_at = utc_now()
        self.agents[worker_id] = {
            "id": worker_id, "name": worker_id.replace("-", " ").title(),
            "responsibility": responsibility, "status": "running", "run_id": self.run_id,
            "last_started_at": started_at, "last_finished_at": None, "duration_ms": None,
            "records_in": records_in, "records_out": 0, "records_failed": 0,
            "handoffs": [], "latest_error": None,
        }
        try:
            value, meta = fn()
            agent = self.agents[worker_id]
            agent["status"] = meta.get("status", "healthy")
            agent["records_out"] = meta.get("records_out", 0)
            agent["records_failed"] = meta.get("records_failed", 0)
            agent["handoffs"] = meta.get("handoffs", [])
            return value
        except Exception as exc:
            self.agents[worker_id]["status"] = "failed"
            self.agents[worker_id]["latest_error"] = str(exc)
            raise
        finally:
            agent = self.agents[worker_id]
            agent["last_finished_at"] = utc_now()
            agent["duration_ms"] = round((time.perf_counter() - started) * 1000, 2)
            self.events.append({
                "id": str(uuid.uuid4()), "run_id": self.run_id, "timestamp": agent["last_finished_at"],
                "agent_id": worker_id, "level": "error" if agent["status"] == "failed" else "info",
                "event": "run_completed" if agent["status"] != "failed" else "run_failed",
                "message": f"{agent['records_out']} records produced; {agent['records_failed']} rejected",
                "duration_ms": agent["duration_ms"], "records": agent["records_out"],
            })

    def run(self, budget: float, previous_snapshot=None):
        self.run_id = f"run_{uuid.uuid4().hex[:12]}"
        self.agents, self.events = {}, []

        raw = self._worker("source-scout", "Retrieve and parse official WA Lottery data", lambda: (
            self.fetcher(), {"records_out": 0, "handoffs": ["game-analyst"]}
        ))
        self.agents["source-scout"]["records_out"] = len(raw)

        errors = []
        def analyze_job():
            analyzed = []
            for game in raw:
                try:
                    analyzed.append(analyze_game(game, budget))
                except (ValueError, TypeError, KeyError) as exc:
                    errors.append({"id": game.get("Id"), "name": game.get("GameName"), "error": str(exc)})
            status = "degraded" if errors else "healthy"
            return analyzed, {"status": status, "records_out": len(analyzed), "records_failed": len(errors),
                              "handoffs": ["portfolio-planner", "jackpot-sentinel", "change-monitor", "quality-gate"]}
        games = self._worker("game-analyst", "Calculate per-game probabilities and payout metrics", analyze_job, len(raw))

        def portfolio_job():
            plans = {goal: optimize_mix(games, budget, goal) for goal in ("any_win", "top_prize", "expected_value")}
            return plans, {"records_out": 3, "handoffs": ["quality-gate"]}
        def jackpot_job():
            watch = build_jackpot_watchlist(games)
            return watch, {"records_out": len(watch), "handoffs": ["quality-gate"]}
        def change_job():
            alerts = compare_snapshots(previous_snapshot, games)
            return alerts, {"records_out": len(alerts), "handoffs": ["quality-gate"]}

        with ThreadPoolExecutor(max_workers=3, thread_name_prefix="wa-agent") as pool:
            f_plan = pool.submit(self._worker, "portfolio-planner", "Optimize budget plans", portfolio_job, len(games))
            f_jack = pool.submit(self._worker, "jackpot-sentinel", "Rank open top-prize games", jackpot_job, len(games))
            f_change = pool.submit(self._worker, "change-monitor", "Detect source-data changes", change_job, len(games))
            plans, watchlist, alerts = f_plan.result(), f_jack.result(), f_change.result()

        def gate_job():
            checks = []
            checks.append(len(games) + len(errors) == len(raw))
            checks.append(all(0 <= g["chance_any_win"] <= 1 and 0 <= g["chance_top_prize"] <= 1 for g in games))
            game_ids = {g["id"] for g in games}
            checks.append(all(item["id"] in game_ids for plan in plans.values() for item in plan["items"]))
            checks.append(all(g["id"] in game_ids and g["top_prizes_remaining"] > 0 for g in watchlist))
            if not all(checks):
                raise ValueError("Quality gate rejected contradictory worker outputs")
            verdict = "publish_degraded" if errors else "publish"
            return {"verdict": verdict, "checks_passed": len(checks), "checks_failed": 0,
                    "warnings": [f"{len(errors)} games quarantined"] if errors else []}, {
                        "status": "degraded" if errors else "healthy", "records_out": len(checks), "handoffs": ["results-ui"]}
        quality = self._worker("quality-gate", "Validate revisions, counts, and probability invariants", gate_job, len(games))

        return {
            "source": SOURCE_URL, "checked_at": utc_now(), "budget": budget, "games": games,
            "jackpot_watchlist": watchlist, "plans": plans, "alerts": alerts, "errors": errors,
            "quality": quality, "run_id": self.run_id,
            "operations": {"generated_at": utc_now(), "run_id": self.run_id,
                           "agents": list(self.agents.values()), "events": sorted(self.events, key=lambda e: e["timestamp"], reverse=True)},
            "method": "Estimated remaining tickets = published overall-odds denominator × reported remaining winning prizes.",
        }
