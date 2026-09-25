import math
import re
from typing import Any


def _number(value: Any) -> float:
    return float(str(value).replace("$", "").replace(",", "").strip())


def _cash_value(label: str):
    cleaned = label.replace("$", "").replace(",", "").strip()
    return float(cleaned) if re.fullmatch(r"\d+(?:\.\d+)?", cleaned) else None


def affordable_tickets(budget: float, cost: float) -> int:
    if budget < 0 or cost <= 0:
        return 0
    return math.floor(budget / cost)


def probability_at_least_one(per_ticket_probability: float, ticket_count: int) -> float:
    if ticket_count <= 0 or per_ticket_probability <= 0:
        return 0.0
    return 1 - (1 - min(per_ticket_probability, 1.0)) ** ticket_count


def tickets_for_target_probability(per_ticket_probability: float, target_probability: float) -> int:
    if per_ticket_probability <= 0 or target_probability <= 0:
        return 0
    if per_ticket_probability >= 1:
        return 1
    target = min(target_probability, 1 - 1e-15)
    return math.ceil(math.log(1 - target) / math.log(1 - per_ticket_probability))


def analyze_game(game: dict, budget: float) -> dict:
    cost = float(game["Cost"])
    odds_text = str(game.get("OverallOdds", ""))
    match = re.search(r"1\s+in\s+([0-9.]+)", odds_text, re.I)
    if not match:
        raise ValueError(f"Invalid overall odds for game {game.get('Id')}: {odds_text}")
    odds = float(match.group(1))
    prizes = game.get("Prizes") or []
    if not prizes:
        raise ValueError(f"No prize tiers for game {game.get('Id')}")

    remaining_winners = sum(int(p["PrizesRemainingNumber"]) for p in prizes)
    total_winners = sum(int(p["TotalPrizesNumber"]) for p in prizes)
    estimated_remaining_tickets = odds * remaining_winners
    ticket_count = affordable_tickets(budget, cost)
    p_any = 1 / odds

    top = prizes[0]
    top_remaining = int(top["PrizesRemainingNumber"])
    top_total = int(top["TotalPrizesNumber"])
    p_top = top_remaining / estimated_remaining_tickets if estimated_remaining_tickets else 0.0
    top_one_in = (1 / p_top) if p_top else None
    spend_1pct = tickets_for_target_probability(p_top, 0.01) * cost if p_top else None
    spend_5pct = tickets_for_target_probability(p_top, 0.05) * cost if p_top else None
    spend_50pct = tickets_for_target_probability(p_top, 0.50) * cost if p_top else None

    unknown_labels = []
    remaining_value = 0.0
    profit_remaining = 0
    for prize in prizes:
        label = str(prize["PrizeAmount"])
        value = _cash_value(label)
        count = int(prize["PrizesRemainingNumber"])
        if value is None:
            unknown_labels.append(label)
        else:
            remaining_value += value * count
            if value > cost:
                profit_remaining += count

    ev_complete = not unknown_labels and estimated_remaining_tickets > 0
    gross_ev = remaining_value / estimated_remaining_tickets if ev_complete else None
    return_rate = gross_ev / cost if gross_ev is not None and cost else None
    p_profit = profit_remaining / estimated_remaining_tickets if estimated_remaining_tickets else 0.0

    chance_no_prize = (1 - p_any) ** ticket_count if ticket_count else 1.0
    chance_exactly_one = ticket_count * p_any * ((1 - p_any) ** (ticket_count - 1)) if ticket_count else 0.0
    chance_two_plus = max(0.0, 1 - chance_no_prize - chance_exactly_one)
    payout_std = None
    if ev_complete:
        second_moment = sum((_cash_value(str(p["PrizeAmount"])) ** 2) * int(p["PrizesRemainingNumber"]) for p in prizes) / estimated_remaining_tickets
        payout_std = math.sqrt(max(0.0, ticket_count * (second_moment - gross_ev ** 2)))

    printed = _number(game.get("TicketsPrinted", 0) or 0)
    alternate_remaining = printed * remaining_winners / total_winners if total_winners else 0.0
    prize_tiers = []
    for prize in prizes:
        remaining = int(prize["PrizesRemainingNumber"])
        total = int(prize["TotalPrizesNumber"])
        paid = int(prize.get("PrizesPaidNumber", total - remaining))
        tier_probability = remaining / estimated_remaining_tickets if estimated_remaining_tickets else 0.0
        tier_value = _cash_value(str(prize["PrizeAmount"]))
        prize_tiers.append({
            "label": str(prize["PrizeAmount"]), "total": total, "paid": paid, "remaining": remaining,
            "percent_remaining": remaining / total if total else 0.0,
            "estimated_probability": tier_probability,
            "estimated_one_in": 1 / tier_probability if tier_probability else None,
            "chance_with_budget": probability_at_least_one(tier_probability, ticket_count),
            "cash_value": tier_value,
            "expected_value_contribution": tier_probability * tier_value if tier_value is not None else None,
        })

    return {
        "id": game["Id"], "name": game["GameName"], "cost": cost,
        "overall_odds": odds, "tickets_affordable": ticket_count,
        "chance_any_win_per_ticket": p_any,
        "chance_any_win": probability_at_least_one(p_any, ticket_count),
        "chance_no_prize": chance_no_prize,
        "chance_exactly_one_prize": chance_exactly_one,
        "chance_two_or_more_prizes": chance_two_plus,
        "expected_winning_tickets": ticket_count * p_any,
        "chance_profit": probability_at_least_one(p_profit, ticket_count),
        "top_prize_label": str(top["PrizeAmount"]),
        "top_prizes_remaining": top_remaining, "top_prizes_total": top_total,
        "estimated_top_prize_probability": p_top,
        "top_prize_one_in": top_one_in,
        "top_prize_expected_spend": top_one_in * cost if top_one_in is not None else None,
        "spend_for_1pct_top_prize": spend_1pct,
        "spend_for_5pct_top_prize": spend_5pct,
        "spend_for_50pct_top_prize": spend_50pct,
        "chance_top_prize": probability_at_least_one(p_top, ticket_count),
        "estimated_remaining_tickets": round(estimated_remaining_tickets),
        "alternate_remaining_ticket_estimate": round(alternate_remaining),
        "estimated_gross_ev": gross_ev, "estimated_net_ev": gross_ev - cost if gross_ev is not None else None,
        "estimated_budget_return": gross_ev * ticket_count if gross_ev is not None else None,
        "estimated_budget_net": (gross_ev - cost) * ticket_count if gross_ev is not None else None,
        "payout_standard_deviation": payout_std,
        "return_rate": return_rate, "ev_complete": ev_complete,
        "unknown_prize_labels": unknown_labels,
        "prize_tiers": prize_tiers,
        "grid_image_url": game.get("GridImageUrl", ""),
        "last_updated": game.get("LastUpdated", ""),
    }
