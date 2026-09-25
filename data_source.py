import json
import re
import urllib.request

SOURCE_URL = "https://walottery.com/Scratch/explorer.aspx"
# The main Scratch page embeds the same game dataset; used if the explorer fails.
FALLBACK_URLS = ("https://www.walottery.com/Scratch/",)


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


def _fetch_html(url: str, timeout: int) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 WA-Scratch-Advisor/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_games(timeout: int = 30, fetch_html=_fetch_html) -> list[dict]:
    """Read the official game dataset, trying the backup page if the explorer fails."""
    errors = []
    for url in (SOURCE_URL, *FALLBACK_URLS):
        try:
            return extract_games(fetch_html(url, timeout))
        except Exception as exc:  # network error or page layout change
            errors.append(f"{url}: {exc}")
    raise ValueError("All WA Lottery sources failed: " + "; ".join(errors))
