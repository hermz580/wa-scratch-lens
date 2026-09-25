import re


def _prize_value(label: str) -> float:
    cleaned = str(label).replace("$", "").replace(",", "").strip()
    return float(cleaned) if re.fullmatch(r"\d+(?:\.\d+)?", cleaned) else -1.0


def build_jackpot_watchlist(games: list[dict]) -> list[dict]:
    result = []
    for game in games:
        if game.get("top_prizes_remaining", 0) <= 0 or not game.get("top_prize_one_in"):
            continue
        item = dict(game)
        item["minimum_entry_spend"] = game["cost"]
        item["top_prize_numeric"] = _prize_value(game.get("top_prize_label", ""))
        result.append(item)
    return sorted(result, key=lambda g: (-g["top_prize_numeric"], g["top_prize_one_in"], g["cost"]))
