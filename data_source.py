import json
import re
import time
import urllib.request
from urllib.error import URLError

SOURCE_URL = "https://walottery.com/Scratch/explorer.aspx"
# The main Scratch page embeds the same game dataset; used if the explorer fails.
FALLBACK_URLS = ("https://www.walottery.com/Scratch/",)


def extract_games(html: str) -> tuple[list[dict], dict]:
    """Extract games from HTML and return (games, metadata)."""
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
    if len(games) == 0:
        raise ValueError("WA Lottery returned empty game list")
    # Validate first game has required fields (case-insensitive for ID)
    sample = games[0]
    if not isinstance(sample, dict):
        raise ValueError("WA Lottery game data structure is invalid")
    has_id = "ID" in sample or "Id" in sample
    has_tiers = "Tiers" in sample
    if not (has_id and has_tiers):
        raise ValueError("WA Lottery game data structure is invalid")
    metadata = {
        "game_count": len(games),
        "generated_at": payload.get("GeneratedAt"),
    }
    return games, metadata


def _fetch_html(url: str, timeout: int, max_retries: int = 3) -> str:
    """Fetch HTML with exponential backoff retry on network errors."""
    delays = [2, 4, 8]  # seconds: 2s, 4s, 8s
    last_error = None
    for attempt in range(max_retries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 WA-Scratch-Advisor/1.0"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read().decode("utf-8", errors="replace")
        except (URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < max_retries - 1:
                time.sleep(delays[attempt])
                continue
            raise ValueError(f"Network error after {max_retries} attempts: {exc}") from exc
    raise last_error or ValueError("Unknown error fetching HTML")


def fetch_games(timeout: int = 30, fetch_html=_fetch_html) -> tuple[list[dict], dict]:
    """Read the official game dataset, trying the backup page if the explorer fails.

    Returns (games, metadata) where metadata contains game_count and generated_at timestamp.
    """
    errors = []
    for url in (SOURCE_URL, *FALLBACK_URLS):
        try:
            return extract_games(fetch_html(url, timeout))
        except Exception as exc:  # network error or page layout change
            errors.append(f"{url}: {exc}")
    raise ValueError("All WA Lottery sources failed: " + "; ".join(errors))
