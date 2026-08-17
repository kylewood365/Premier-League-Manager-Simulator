"""AI offers and deliberately simple transfer negotiations."""

import random

from morale import form_score


ACTIVE_STATUSES = {"Pending", "Countered"}
MAX_NEGOTIATION_ROUNDS = 3


def offer_probability(player):
    """Return the per-gameweek chance that a player attracts interest."""
    chance = 0.025
    if player.get("transfer_listed"):
        chance += 0.28
    if player.get("transfer_requested"):
        chance += 0.22
    recent_form = form_score(player)
    if recent_form is not None:
        chance += max(0, recent_form - 6) * 0.025
    chance += max(0, player.get("overall", 0) - 78) * 0.008
    if player.get("age", 30) <= 23:
        chance += max(0, player.get("potential", 0) - player.get("overall", 0)) * 0.012
    return min(0.80, chance)


def calculate_offer_fee(player, rng=None):
    """Create a testable offer normally between 85% and 120% of value."""
    rng = rng or random
    low, high = 0.85, 1.20
    recent_form = form_score(player)
    if recent_form is not None and recent_form >= 8:
        high += 0.10
    if player.get("age", 30) <= 23 and player.get("potential", 0) >= 85:
        high += 0.10
    if player.get("transfer_listed") or player.get("transfer_requested"):
        low -= 0.05
    fee = player["value"] * rng.uniform(low, high)
    return max(100_000, int(round(fee / 100_000) * 100_000))


def _active_duplicate(offers, club, player_name):
    return any(
        offer["buying_club"] == club
        and offer["player"] == player_name
        and offer["status"] in ACTIVE_STATUSES
        for offer in offers
    )


def generate_ai_offers(squads, user_club, club_budgets, offers, gameweek,
                       season=1, processed_gameweeks=None, rng=None):
    """Generate at most one set of offers for a completed league gameweek."""
    rng = rng or random
    processed_gameweeks = processed_gameweeks if processed_gameweeks is not None else set()
    marker = (season, gameweek)
    if marker in processed_gameweeks:
        return []
    processed_gameweeks.add(marker)
    expire_offers(offers, gameweek, season)
    created = []
    clubs = [club for club in squads if club != user_club]
    for player in list(squads[user_club]):
        if rng.random() >= offer_probability(player):
            continue
        affordable = [club for club in clubs if club_budgets.get(club, 0) >= player["value"] * 0.80]
        if not affordable:
            continue
        buying_club = rng.choice(affordable)
        if _active_duplicate(offers, buying_club, player["name"]):
            continue
        fee = min(calculate_offer_fee(player, rng), club_budgets[buying_club])
        offer = {
            "id": max((item["id"] for item in offers), default=0) + 1,
            "player": player["name"], "buying_club": buying_club,
            "offered_fee": fee, "original_fee": fee, "status": "Pending",
            "negotiation_round": 0, "created_gameweek": gameweek,
            "season": season,
        }
        offers.append(offer)
        created.append(offer)
    return created


def expire_offers(offers, gameweek, season=1, lifetime=2):
    """Withdraw offers after two later gameweeks, never on creation."""
    for offer in offers:
        if (offer["status"] in ACTIVE_STATUSES and offer.get("season", season) == season
                and gameweek > offer.get("created_gameweek", gameweek)
                and gameweek - offer.get("created_gameweek", gameweek) >= lifetime):
            offer["status"] = "Withdrawn"
    return offers


def reject_offer(offer):
    """Reject an active offer without changing financial or squad state."""
    if offer["status"] not in ACTIVE_STATUSES:
        return False
    offer["status"] = "Rejected"
    return True


def counter_offer(offer, requested_fee, player, club_budgets, rng=None):
    """Let the AI accept, improve, or withdraw after a manager counter."""
    if offer["status"] not in ACTIVE_STATUSES:
        return "Withdrawn"
    if offer["negotiation_round"] >= MAX_NEGOTIATION_ROUNDS:
        offer["status"] = "Withdrawn"
        return "Withdrawn"
    offer["negotiation_round"] += 1
    club = offer["buying_club"]
    if requested_fee > club_budgets.get(club, 0):
        offer["status"] = "Withdrawn"
        return "Withdrawn"
    value = player["value"]
    ceiling = value * (1.25 + (0.10 if player.get("age", 30) <= 23 else 0))
    if requested_fee <= max(value * 1.05, offer["offered_fee"] * 1.08):
        offer["offered_fee"] = int(requested_fee)
        offer["status"] = "Pending"
        return "Accepted"
    if requested_fee <= ceiling and offer["negotiation_round"] < MAX_NEGOTIATION_ROUNDS:
        improved = min(requested_fee, int((offer["offered_fee"] + requested_fee) / 2))
        offer["offered_fee"] = min(improved, club_budgets[club])
        offer["status"] = "Countered"
        return "Improved"
    offer["status"] = "Withdrawn"
    return "Withdrawn"


def accept_offer(offer, squads, user_club, club_budgets, transfer_history,
                 season=1):
    """Complete an AI purchase exactly once and preserve the player record."""
    if offer["status"] not in ACTIVE_STATUSES:
        return False, "This offer is no longer active."
    player = next((p for p in squads[user_club] if p["name"] == offer["player"]), None)
    club, fee = offer["buying_club"], offer["offered_fee"]
    if player is None:
        return False, "The player is no longer in your squad."
    if club == user_club or club_budgets.get(club, 0) < fee:
        offer["status"] = "Withdrawn"
        return False, "The buying club can no longer complete this transfer."
    squads[user_club].remove(player)
    player["club"] = club
    player["transfer_requested"] = False
    player["transfer_listed"] = False
    player["playing_time_promise"] = None
    for key in ("squad_role", "role_satisfaction", "available_league_games",
                "participated_league_games", "playing_time_history",
                "very_unhappy_weeks", "last_squad_management_gameweek"):
        player.pop(key, None)
    squads[club].append(player)
    club_budgets[user_club] += fee
    club_budgets[club] -= fee
    offer["status"] = "Accepted"
    transfer_history.append({
        "season": season, "player": player["name"], "from_club": user_club,
        "to_club": club, "fee": fee, "type": "Sell",
    })
    return True, f"{player['name']} has joined {club} for £{fee:,.0f}."


def handle_new_season_offers(offers):
    """Withdraw negotiations left open when a new season starts."""
    for offer in offers:
        if offer["status"] in ACTIVE_STATUSES:
            offer["status"] = "Withdrawn"
    return offers
