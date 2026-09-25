import json
from datetime import datetime, timezone
from pathlib import Path


def load_snapshot(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_snapshot(path: Path, games: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(games, indent=2), encoding="utf-8")


def compare_snapshots(old, current):
    if old is None:
        return []
    prior = {str(item["id"]): item for item in old}
    alerts = []
    now = datetime.now(timezone.utc).isoformat()
    for game in current:
        key = str(game["id"])
        before = prior.get(key)
        if not before:
            alerts.append({"kind": "new_game", "game": game["name"], "message": "New game added", "detected_at": now})
            continue
        old_top = before.get("top_prizes_remaining")
        new_top = game.get("top_prizes_remaining")
        if old_top != new_top:
            alerts.append({"kind": "top_prize_change", "game": game["name"], "previous": old_top, "current": new_top,
                           "message": f"Top prizes remaining changed from {old_top} to {new_top}", "detected_at": now})
    return alerts
