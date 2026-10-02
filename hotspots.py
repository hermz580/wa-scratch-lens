"""Winning Hotspots: stores that sold big ($600+) scratch and draw winners.

WA Lottery's winners page embeds one record per store (name, city, map
position, a winning amount). It lists each store once and carries no game
or date, so this module keeps its own history: when a store first appears
and every time its listed amount changes, which we count as a new win
seen. Over time that gives real "most winners" counts.

Writes docs/data/hotspots.json (read by the app) and keeps its history in
docs/data/hotspots_history.json. A failure here never blocks game data.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from data_source import _fetch_html

HOTSPOTS_URL = "https://www.walottery.com/winners/"
MARKER = "WinningHotspots.mapData = JSON.parse('"
DATA_DIR = Path(__file__).parent / "docs" / "data"
NEW_STORE_DAYS = 14
MAX_EVENTS = 100


def extract_hotspots(html: str) -> list[dict]:
    """Pull the store list out of the winners page HTML."""
    start = html.find(MARKER)
    if start < 0:
        raise ValueError("WA Lottery hotspot data was not found")
    start += len(MARKER)
    end = html.find("')", start)
    if end < 0:
        raise ValueError("WA Lottery hotspot data was incomplete")
    try:
        payload = json.loads(html[start:end].replace("\\'", "'"))
    except json.JSONDecodeError as exc:
        raise ValueError("WA Lottery hotspot data could not be decoded") from exc
    locations = payload.get("Locations")
    if not isinstance(locations, list) or not locations:
        raise ValueError("WA Lottery hotspot data has no Locations")
    stores = []
    for loc in locations:
        try:
            stores.append({
                "id": str(loc["Number"]),
                "name": str(loc["Name"]).strip(),
                "address": str(loc.get("Address") or "").strip(),
                "city": str(loc["City"]).strip().title(),
                "lat": round(float(loc["Lattitude"]), 5),  # sic: WA's spelling
                "lon": round(float(loc["Longitude"]), 5),
                "amount": float(loc.get("WinningAmount") or 0),
            })
        except (KeyError, TypeError, ValueError):
            continue  # skip one malformed store, keep the rest
    if not stores:
        raise ValueError("WA Lottery hotspot data had no usable stores")
    return stores


def fetch_hotspots(timeout: int = 30, fetch_html=_fetch_html) -> list[dict]:
    return extract_hotspots(fetch_html(HOTSPOTS_URL, timeout))


def build(stores: list[dict], history: dict | None, now: datetime) -> tuple[dict, dict]:
    """Pure transform: stores + prior history -> (app payload, new history)."""
    now_iso = now.isoformat(timespec="seconds")
    baseline = not history or not history.get("stores")
    known = (history or {}).get("stores", {})
    events = list((history or {}).get("events", []))

    new_known, out = {}, []
    for s in stores:
        prev = known.get(s["id"])
        if prev is None:
            rec = {"first_seen": None if baseline else now_iso, "wins_seen": 1, "amount": s["amount"]}
            if not baseline:
                events.append({"t": now_iso, "id": s["id"], "name": s["name"], "city": s["city"],
                               "amount": s["amount"], "message": f"New ${s['amount']:,.0f} winner sold at {s['name']}, {s['city']}"})
        else:
            rec = dict(prev)
            if s["amount"] != prev.get("amount"):
                rec["wins_seen"] = prev.get("wins_seen", 1) + 1
                rec["amount"] = s["amount"]
                events.append({"t": now_iso, "id": s["id"], "name": s["name"], "city": s["city"],
                               "amount": s["amount"], "message": f"Another ${s['amount']:,.0f} winner at {s['name']}, {s['city']}"})
        rec["last_seen"] = now_iso
        new_known[s["id"]] = rec
        fresh = bool(rec["first_seen"]) and now - datetime.fromisoformat(rec["first_seen"]) <= timedelta(days=NEW_STORE_DAYS)
        out.append({**s, "wins": rec["wins_seen"], "is_new": fresh})
    for key, old in known.items():  # remember stores that drop off the map
        new_known.setdefault(key, old)

    cities = defaultdict(lambda: {"stores": 0, "wins": 0, "total": 0.0, "biggest": 0.0})
    for s in out:
        c = cities[s["city"]]
        c["stores"] += 1
        c["wins"] += s["wins"]
        c["total"] += s["amount"]
        c["biggest"] = max(c["biggest"], s["amount"])
    city_rows = sorted(({"city": k, **v} for k, v in cities.items()), key=lambda r: (-r["wins"], -r["total"]))

    out.sort(key=lambda s: (-s["wins"], -s["amount"]))
    events = events[-MAX_EVENTS:]
    payload = {"generated_at": now_iso, "source_url": HOTSPOTS_URL, "store_count": len(out),
               "stores": out, "cities": city_rows, "events": list(reversed(events[-20:]))}
    return payload, {"version": 1, "stores": new_known, "events": events}


def run(data_dir: Path = DATA_DIR, fetcher=fetch_hotspots, now: datetime | None = None) -> bool:
    """Fetch, build and write. Returns True when the store list changed."""
    now = now or datetime.now(timezone.utc)
    stores = fetcher()
    hist_path, out_path = data_dir / "hotspots_history.json", data_dir / "hotspots.json"
    history = json.loads(hist_path.read_text(encoding="utf-8")) if hist_path.exists() else None
    snapshot = sorted([s["id"], s["amount"]] for s in stores)
    if history and history.get("snapshot") == snapshot and out_path.exists():
        return False
    payload, new_history = build(stores, history, now)
    new_history["snapshot"] = snapshot
    data_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    hist_path.write_text(json.dumps(new_history, separators=(",", ":")), encoding="utf-8")
    return True


if __name__ == "__main__":
    try:
        print("Hotspots updated" if run() else "No change in hotspots")
    except Exception as exc:  # never fail the data job over the bonus feature
        print(f"Hotspots skipped: {exc}", file=sys.stderr)
