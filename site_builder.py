"""Build the phone app's data files from the live WA Lottery feed.

Run by the scheduled GitHub Action (and by server.py locally). Writes:
  docs/data/latest.json  - scored games + recent events, read by the app
  docs/data/history.json - first-seen dates, daily snapshots, event log

Files are only rewritten when the lottery data actually changed, so the
scheduled job does not create empty commits.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from data_source import SOURCE_URL, fetch_games
from smart_score import game_metrics, score, trend

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "docs" / "data"
CHECK_MINUTES = [7, 37]  # keep in sync with .github/workflows/update-data.yml
NEW_GAME_DAYS = 30
MAX_POINTS = 120
MAX_EVENTS = 200


def fingerprint(raw_games: list[dict]) -> str:
    slim = sorted((g["Id"], g.get("Cost"), [(p["PrizeAmount"], p["PrizesRemainingNumber"]) for p in g.get("Prizes") or []])
                  for g in raw_games)
    return hashlib.sha256(json.dumps(slim).encode()).hexdigest()[:16]


def _event(now: str, kind: str, game: dict, message: str) -> dict:
    return {"t": now, "kind": kind, "id": game["id"], "name": game["name"], "cost": game["cost"], "message": message}


def build(raw_games: list[dict], history: dict | None, now: datetime) -> tuple[dict, dict]:
    """Pure transform: raw feed + prior history -> (latest payload, new history)."""
    now_iso = now.isoformat(timespec="seconds")
    today = now.date().isoformat()
    baseline = not history or not history.get("games")
    history = history or {}
    known = history.get("games", {})
    events = list(history.get("events", []))

    games, errors = [], []
    for raw in raw_games:
        try:
            games.append(score(game_metrics(raw)))
        except (ValueError, TypeError, KeyError) as exc:
            errors.append({"id": raw.get("Id"), "error": str(exc)})

    new_known = {}
    live_ids = set()
    for g in games:
        key = str(g["id"])
        live_ids.add(key)
        prev = known.get(key)
        if prev is None:
            prev = {"first_seen": None if baseline else now_iso, "points": []}
            if not baseline:
                events.append(_event(now_iso, "new_game", g, f"New ${g['cost']:.0f} ticket: {g['name']} — top prize {g['top_label']}"))
        else:
            old_top = prev.get("top_rem")
            if old_top is not None and g["top_rem"] < old_top:
                claimed = old_top - g["top_rem"]
                msg = (f"{claimed} top prize{'s' if claimed > 1 else ''} ({g['top_label']}) claimed — "
                       f"{g['top_rem']} of {g['top_total']} left")
                events.append(_event(now_iso, "top_claimed" if g["top_rem"] else "top_gone", g, msg))
        points = [p for p in prev.get("points", []) if p["t"] != today]
        points.append({"t": today, "rw": g["rem_winners"], "top": g["top_rem"], "rtp": round(g["rtp"], 4)})
        points = points[-MAX_POINTS:]
        new_known[key] = {"name": g["name"], "cost": g["cost"], "first_seen": prev.get("first_seen"),
                          "last_seen": now_iso, "top_rem": g["top_rem"], "points": points}

        g.update(trend(points, g["odds"], g["est_remaining"]))
        g["first_seen"] = new_known[key]["first_seen"]
        seen_recently = g["first_seen"] and now - datetime.fromisoformat(g["first_seen"]) <= timedelta(days=NEW_GAME_DAYS)
        g["is_new"] = bool(seen_recently or g["sold_pct"] < 0.03)

    for key, old in known.items():
        if key not in live_ids and not old.get("retired_at"):
            retired = {**old, "retired_at": now_iso}
            new_known[key] = retired
            events.append({"t": now_iso, "kind": "retired", "id": int(key) if key.isdigit() else key,
                           "name": old["name"], "cost": old["cost"], "message": f"{old['name']} was removed from the active list"})
        elif key not in live_ids:
            new_known[key] = old

    events = events[-MAX_EVENTS:]
    games.sort(key=lambda g: (-g["score"], -g["rtp"]))
    for rank, g in enumerate(games, 1):
        g["rank"] = rank
        del g["rem_winners"]

    source_updated = max((g["source_updated"] for g in games), default="", key=_source_time)
    latest = {
        "generated_at": now_iso, "source_url": SOURCE_URL, "source_updated": source_updated,
        "check_minutes": CHECK_MINUTES, "game_count": len(games), "errors": errors,
        "games": games, "events": list(reversed(events[-40:])),
    }
    new_history = {"version": 1, "fingerprint": fingerprint(raw_games), "games": new_known, "events": events}
    return latest, new_history


def _source_time(text: str):
    try:
        return datetime.strptime(text, "%m/%d/%Y %I:%M:%S %p")
    except ValueError:
        return datetime.min


def _rounded(value):
    if isinstance(value, float):
        return float(f"{value:.6g}")
    if isinstance(value, dict):
        return {k: _rounded(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_rounded(v) for v in value]
    return value


def run(data_dir: Path = DATA_DIR, fetcher=fetch_games, now: datetime | None = None, force: bool = False) -> bool:
    """Fetch, build and write. Returns True when files changed."""
    now = now or datetime.now(timezone.utc)
    raw = fetcher()
    if not raw:
        raise ValueError("WA Lottery feed returned no games")
    history_path, latest_path = data_dir / "history.json", data_dir / "latest.json"
    history = json.loads(history_path.read_text(encoding="utf-8")) if history_path.exists() else None
    if not force and history and history.get("fingerprint") == fingerprint(raw) and latest_path.exists():
        return False
    latest, new_history = build(raw, history, now)
    data_dir.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(json.dumps(_rounded(latest), separators=(",", ":")), encoding="utf-8")
    history_path.write_text(json.dumps(new_history, separators=(",", ":")), encoding="utf-8")
    return True


if __name__ == "__main__":
    changed = run(force="--force" in sys.argv)
    print("Data updated" if changed else "No change in WA Lottery data")
