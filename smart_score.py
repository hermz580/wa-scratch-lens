"""Smart Score: ranks scratch games by how good the *remaining* ticket pool looks.

Every game is scored from the official prize table alone:

* value   - estimated cents returned per $1 on the tickets still out there
* drift   - how that return compares with the game's return at launch
            (positive = the big prizes are outlasting the small ones)
* richness- share of the top-3 prize tiers left vs. share of all winners left

No score makes a game profitable on average. It only separates the
better-value remaining pools from the worse ones.
"""
from __future__ import annotations

import html
import math
import re

VALUE_FLOOR, VALUE_CEIL = 0.55, 0.85
DRIFT_SPAN = 0.08
RICH_FLOOR, RICH_SPAN = 0.6, 0.8
WEIGHTS = {"value": 0.45, "drift": 0.30, "richness": 0.25}
TOP_GONE_PENALTY = 0.55
NEW_GAME_SOLD_PCT = 0.03


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def prize_value(label: str):
    """Return (dollar value, is_approximate) or (None, False) for non-cash prizes."""
    text = html.unescape(str(label)).replace(",", "").strip()
    plain = re.fullmatch(r"\$?\s*(\d+(?:\.\d+)?)", text)
    if plain:
        return float(plain.group(1)), False
    annuity = re.fullmatch(r"\$?\s*(\d+(?:\.\d+)?)\s*/\s*(?:yr|year)\s*/\s*(\d+)\s*(?:yrs?|years?)", text, re.I)
    if annuity:
        return float(annuity.group(1)) * int(annuity.group(2)), True
    return None, False


def parse_odds(text: str) -> float:
    match = re.search(r"1\s+in\s+([0-9.,]+)", str(text), re.I)
    if not match:
        raise ValueError(f"Invalid overall odds: {text}")
    return float(match.group(1).replace(",", ""))


def game_metrics(game: dict) -> dict:
    """Budget-independent metrics for one raw WA Lottery game record."""
    cost = float(game["Cost"])
    odds = parse_odds(game.get("OverallOdds", ""))
    prizes = game.get("Prizes") or []
    if cost <= 0 or not prizes:
        raise ValueError(f"Game {game.get('Id')} has no price or prize tiers")

    total_w = sum(int(p["TotalPrizesNumber"]) for p in prizes)
    rem_w = sum(int(p["PrizesRemainingNumber"]) for p in prizes)
    est_remaining = odds * rem_w
    est_printed = odds * total_w

    tiers, rem_value, launch_value, profit_rem = [], 0.0, 0.0, 0
    unknown, approximate = [], False
    for p in prizes:
        label = html.unescape(str(p["PrizeAmount"]))
        total, rem = int(p["TotalPrizesNumber"]), int(p["PrizesRemainingNumber"])
        value, approx = prize_value(label)
        approximate = approximate or approx
        if value is None:
            unknown.append(label)
        else:
            rem_value += value * rem
            launch_value += value * total
            if value > cost:
                profit_rem += rem
        tiers.append({"label": label, "value": value, "total": total, "rem": rem,
                      "p": rem / est_remaining if est_remaining else 0.0})

    top = prizes[0]
    top_total, top_rem = int(top["TotalPrizesNumber"]), int(top["PrizesRemainingNumber"])
    top3_total = sum(int(p["TotalPrizesNumber"]) for p in prizes[:3])
    top3_rem = sum(int(p["PrizesRemainingNumber"]) for p in prizes[:3])
    share_left = rem_w / total_w if total_w else 0.0
    richness = (top3_rem / top3_total) / share_left if top3_total and share_left else 0.0

    rtp = rem_value / est_remaining / cost if est_remaining else 0.0
    launch_rtp = launch_value / est_printed / cost if est_printed else 0.0
    p_top = top_rem / est_remaining if est_remaining else 0.0
    return {
        "id": game["Id"], "name": html.unescape(str(game["GameName"])), "cost": cost,
        "img": game.get("GridImageUrl", ""), "odds": odds,
        "printed": est_printed, "sold_pct": 1 - share_left,
        "est_remaining": round(est_remaining),
        "rtp": rtp, "launch_rtp": launch_rtp, "drift": rtp - launch_rtp,
        "rtp_is_floor": bool(unknown), "rtp_is_approx": approximate, "unknown_prizes": unknown,
        "richness": richness,
        "top_label": html.unescape(str(top["PrizeAmount"])), "top_value": prize_value(top["PrizeAmount"])[0],
        "top_rem": top_rem, "top_total": top_total,
        "p_any": 1 / odds, "p_profit": profit_rem / est_remaining if est_remaining else 0.0,
        "p_top": p_top, "top_one_in": 1 / p_top if p_top else None,
        "tiers": tiers, "rem_winners": rem_w,
        "source_updated": game.get("LastUpdated", ""),
    }


def score(m: dict) -> dict:
    """Attach smart score (0-100), verdict and plain-English reasons to metrics."""
    value_s = clamp((m["rtp"] - VALUE_FLOOR) / (VALUE_CEIL - VALUE_FLOOR))
    drift_s = clamp(0.5 + m["drift"] / DRIFT_SPAN)
    rich_s = clamp((m["richness"] - RICH_FLOOR) / RICH_SPAN)
    raw = WEIGHTS["value"] * value_s + WEIGHTS["drift"] * drift_s + WEIGHTS["richness"] * rich_s
    top_gone = m["top_rem"] <= 0
    if top_gone:
        raw *= TOP_GONE_PENALTY
    points = round(raw * 100)

    if top_gone:
        verdict = "skip"
    elif points >= 70:
        verdict = "best"
    elif points >= 55:
        verdict = "good"
    elif points >= 40:
        verdict = "fair"
    else:
        verdict = "skip"

    cents = round(m["rtp"] * 100)
    reasons = []
    prefix = "at least " if m["rtp_is_floor"] else "about "
    reasons.append(f"Pays back {prefix}{cents}¢ per $1 on the tickets left")
    drift_pts = m["drift"] * 100
    if drift_pts >= 1.5:
        reasons.append(f"Remaining pool is richer than at launch (+{drift_pts:.1f} pts)")
    elif drift_pts <= -1.5:
        reasons.append(f"Remaining pool is weaker than at launch ({drift_pts:.1f} pts)")
    if m["richness"] >= 1.1:
        reasons.append(f"Big prizes over-represented: {m['richness']:.2f}× their fair share")
    elif 0 < m["richness"] <= 0.8:
        reasons.append(f"Big prizes under-represented: {m['richness']:.2f}× their fair share")
    if top_gone:
        reasons.append("Every top prize is gone — still on sale, but skip it")
    elif m["top_rem"] == 1:
        reasons.append("Only 1 top prize left")
    if m["sold_pct"] >= 0.9:
        reasons.append(f"Nearly sold out ({m['sold_pct']:.0%} sold) — numbers swing fast")
    elif m["sold_pct"] < NEW_GAME_SOLD_PCT:
        reasons.append("Brand-new game — full prize pool")
    if m["unknown_prizes"]:
        reasons.append("Includes non-cash prizes not counted in the return")
    return {**m, "score": points, "verdict": verdict, "reasons": reasons,
            "parts": {"value": round(value_s, 3), "drift": round(drift_s, 3), "richness": round(rich_s, 3)}}


def trend(points: list[dict], odds: float, est_remaining: float) -> dict:
    """Sell-through speed from history points [{'t': iso date, 'rw': remaining winners}]."""
    if len(points) < 2:
        return {"tickets_per_day": None, "days_left": None}
    from datetime import date
    first, last = points[0], points[-1]
    days = (date.fromisoformat(last["t"][:10]) - date.fromisoformat(first["t"][:10])).days
    sold = (first["rw"] - last["rw"]) * odds
    if days <= 0 or sold <= 0:
        return {"tickets_per_day": None, "days_left": None}
    per_day = sold / days
    return {"tickets_per_day": round(per_day), "days_left": math.ceil(est_remaining / per_day)}
