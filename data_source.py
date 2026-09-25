import json
import re
import urllib.request

SOURCE_URL = "https://walottery.com/Scratch/explorer.aspx"


def extract_games(html: str) -> list[dict]:
    marker = "all: JSON.parse('"
    start = html.find(marker)
    if start < 0:
        raise ValueError("WA Lottery embedded game data was not found")
    start += len(marker)
    end = html.find("')", start)
    if end < 0:
        raise ValueError("WA Lottery embedded game data was incomplete")
    raw = html[start:end]
    try:
        decoded = bytes(raw, "utf-8").decode("unicode_escape")
        payload = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("WA Lottery embedded game data could not be decoded") from exc
    games = payload.get("Games")
    if not isinstance(games, list):
        raise ValueError("WA Lottery embedded game data has no Games list")
    return games


def fetch_games(timeout: int = 30) -> list[dict]:
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0 WA-Scratch-Advisor/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        html = response.read().decode("utf-8", errors="replace")
    return extract_games(html)
