from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from alerts import load_snapshot, save_snapshot
from agent_pipeline import AgentPipeline

ROOT = Path(__file__).parent
STATIC = ROOT / "static"
SNAPSHOT = ROOT / "data" / "snapshot.json"
HISTORY = ROOT / "data" / "watch-history.jsonl"
WATCH_INTERVAL_SECONDS = 15 * 60
PORT = 8879


OPERATIONS_LOCK = threading.Lock()
LAST_OPERATIONS = {"generated_at": None, "run_id": None, "agents": [], "events": []}


class ExclusiveThreadingHTTPServer(ThreadingHTTPServer):
    """Fail loudly instead of co-binding with a stale local instance."""

    allow_reuse_address = False


def build_payload(budget: float):
    global LAST_OPERATIONS
    previous = load_snapshot(SNAPSHOT)
    payload = AgentPipeline().run(budget, previous_snapshot=previous)
    if payload["quality"]["verdict"] in ("publish", "publish_degraded"):
        save_snapshot(SNAPSHOT, payload["games"])
    with OPERATIONS_LOCK:
        LAST_OPERATIONS = payload["operations"]
    return payload


def watch_forever():
    while True:
        try:
            payload = build_payload(20.0)
            leaders = payload["jackpot_watchlist"][:10]
            record = {"checked_at": payload["checked_at"], "leaders": [{
                "id": g["id"], "name": g["name"], "top_prize": g["top_prize_label"],
                "remaining": g["top_prizes_remaining"], "one_in": g["top_prize_one_in"],
                "ticket_cost": g["cost"]} for g in leaders]}
            HISTORY.parent.mkdir(parents=True, exist_ok=True)
            with HISTORY.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record) + "\n")
        except Exception as exc:
            print(f"Watcher cycle failed: {exc}")
        time.sleep(WATCH_INTERVAL_SECONDS)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            with OPERATIONS_LOCK:
                quality = next((a for a in LAST_OPERATIONS["agents"] if a["id"] == "quality-gate"), None)
            return self.send_json({"ok": True, "service": "WA Scratch Advisor", "pipeline": quality["status"] if quality else "starting"})
        if parsed.path == "/api/operations":
            with OPERATIONS_LOCK:
                return self.send_json(LAST_OPERATIONS)
        if parsed.path == "/api/games":
            query = parse_qs(parsed.query)
            try:
                budget = float(query.get("budget", ["20"])[0])
                if budget < 0 or budget > 100000:
                    raise ValueError
                payload = build_payload(budget)
                return self.send_json(payload)
            except ValueError:
                return self.send_json({"error": "Budget must be between $0 and $100,000."}, 400)
            except Exception as exc:
                return self.send_json({"error": "Live WA Lottery data could not be loaded.", "detail": str(exc)}, 502)
        return super().do_GET()

    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    threading.Thread(target=watch_forever, daemon=True, name="lottery-watch-agent").start()
    print(f"WA Scratch Advisor: http://127.0.0.1:{PORT}")
    ExclusiveThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
