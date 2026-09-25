import math


def _utility(game: dict, goal: str) -> float:
    if goal == "any_win":
        p = game.get("chance_any_win_per_ticket") or 0.0
        return -math.log(max(1e-15, 1 - p))
    if goal == "top_prize":
        p = game.get("estimated_top_prize_probability") or 0.0
        return -math.log(max(1e-15, 1 - p))
    if goal == "expected_value":
        return float(game.get("estimated_gross_ev") or 0.0)
    raise ValueError(f"Unknown optimization goal: {goal}")


def optimize_mix(games: list[dict], budget: float, goal: str) -> dict:
    cents = max(0, int(round(budget * 100)))
    eligible = [g for g in games if g.get("cost", 0) > 0 and (goal != "expected_value" or g.get("estimated_gross_ev") is not None)]
    dp = [float("-inf")] * (cents + 1)
    choice = [None] * (cents + 1)
    dp[0] = 0.0
    for amount in range(cents + 1):
        if dp[amount] == float("-inf"):
            continue
        for game in eligible:
            price = int(round(game["cost"] * 100))
            nxt = amount + price
            if nxt <= cents:
                score = dp[amount] + _utility(game, goal)
                if score > dp[nxt]:
                    dp[nxt], choice[nxt] = score, (amount, game)
    spent_cents = max(range(cents + 1), key=lambda i: (dp[i], i)) if eligible else 0
    counts = {}
    cursor = spent_cents
    while cursor and choice[cursor]:
        previous, game = choice[cursor]
        counts[game["id"]] = counts.get(game["id"], 0) + 1
        cursor = previous
    by_id = {g["id"]: g for g in eligible}
    items = [{"id": gid, "name": by_id[gid]["name"], "count": count,
              "cost": round(by_id[gid]["cost"] * count, 2)} for gid, count in counts.items()]
    items.sort(key=lambda item: (-item["cost"], item["name"]))
    spent = round(spent_cents / 100, 2)
    return {"goal": goal, "items": items, "spent": spent, "unspent": round(budget - spent, 2), "score": dp[spent_cents] if spent_cents else 0.0}
