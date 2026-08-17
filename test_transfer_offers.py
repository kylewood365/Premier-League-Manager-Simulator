"""Tests for incoming AI offers and negotiation state."""

from copy import deepcopy
import random

from contracts import calculate_wage_spend
from data import CLUB_BUDGETS, SQUADS
from transfer_offers import (
    accept_offer, calculate_offer_fee, counter_offer, expire_offers,
    generate_ai_offers, offer_probability, reject_offer,
)


def make_offer(player, club="Chelsea", fee=None, gameweek=1):
    amount = fee or player["value"]
    return {"id": 1, "player": player["name"], "buying_club": club,
            "offered_fee": amount, "original_fee": amount, "status": "Pending",
            "negotiation_round": 0, "created_gameweek": gameweek, "season": 1}


def test_listed_and_requested_players_have_higher_offer_chances():
    ordinary = {**SQUADS["Arsenal"][0], "transfer_listed": False,
                "transfer_requested": False}
    listed = {**ordinary, "transfer_listed": True}
    requested = {**ordinary, "transfer_requested": True}
    assert offer_probability(listed) > offer_probability(ordinary)
    assert offer_probability(requested) > offer_probability(ordinary)


def test_offer_values_are_sensible():
    player = {**SQUADS["Arsenal"][0], "form_history": []}
    fees = [calculate_offer_fee(player, random.Random(seed)) for seed in range(30)]
    assert all(player["value"] * .85 <= fee <= player["value"] * 1.20 for fee in fees)


def test_generation_uses_other_affordable_clubs_once_per_week():
    squads = deepcopy(SQUADS)
    for player in squads["Arsenal"]:
        player["transfer_listed"] = True
        player["transfer_requested"] = True
    budgets = dict(CLUB_BUDGETS)
    offers, processed = [], set()
    created = generate_ai_offers(squads, "Arsenal", budgets, offers, 1, 1,
                                 processed, random.Random(4))
    assert created
    assert all(o["buying_club"] != "Arsenal" for o in created)
    assert all(o["offered_fee"] <= budgets[o["buying_club"]] for o in created)
    assert generate_ai_offers(squads, "Arsenal", budgets, offers, 1, 1,
                              processed, random.Random(4)) == []
    assert len({(o["buying_club"], o["player"]) for o in offers}) == len(offers)


def test_accept_moves_player_updates_budgets_wages_and_history_once():
    squads, budgets = deepcopy(SQUADS), dict(CLUB_BUDGETS)
    player = squads["Arsenal"][0]
    fee, before_wages = player["value"], calculate_wage_spend(squads["Arsenal"])
    user_before, ai_before, history = budgets["Arsenal"], budgets["Chelsea"], []
    offer = make_offer(player, fee=fee)
    success, _ = accept_offer(offer, squads, "Arsenal", budgets, history, 1)
    assert success and player in squads["Chelsea"] and player not in squads["Arsenal"]
    assert player["club"] == "Chelsea"
    assert budgets["Arsenal"] == user_before + fee
    assert budgets["Chelsea"] == ai_before - fee
    assert calculate_wage_spend(squads["Arsenal"]) == before_wages - player["wage"]
    assert history[-1]["type"] == "Sell"
    snapshot = deepcopy(budgets)
    assert not accept_offer(offer, squads, "Arsenal", budgets, history, 1)[0]
    assert budgets == snapshot and len(history) == 1


def test_reject_changes_no_squad_or_budget_state():
    squads, budgets = deepcopy(SQUADS), dict(CLUB_BUDGETS)
    before_squads, before_budgets = deepcopy(squads), dict(budgets)
    offer = make_offer(squads["Arsenal"][0])
    assert reject_offer(offer)
    assert squads == before_squads and budgets == before_budgets


def test_reasonable_counter_is_accepted_and_unaffordable_one_withdrawn():
    player = SQUADS["Arsenal"][0]
    budgets = dict(CLUB_BUDGETS)
    reasonable = make_offer(player, fee=player["value"])
    assert counter_offer(reasonable, int(player["value"] * 1.04), player, budgets) == "Accepted"
    expensive = make_offer(player)
    assert counter_offer(expensive, budgets["Chelsea"] + 1, player, budgets) == "Withdrawn"
    assert expensive["status"] == "Withdrawn"


def test_negotiations_are_limited_and_offers_expire_only_later():
    player, budgets = SQUADS["Arsenal"][0], dict(CLUB_BUDGETS)
    offer = make_offer(player)
    offer["negotiation_round"] = 3
    assert counter_offer(offer, player["value"], player, budgets) == "Withdrawn"
    fresh = make_offer(player, gameweek=4)
    expire_offers([fresh], 4)
    assert fresh["status"] == "Pending"
    expire_offers([fresh], 6)
    assert fresh["status"] == "Withdrawn"
