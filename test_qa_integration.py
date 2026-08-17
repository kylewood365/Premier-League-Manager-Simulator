"""Seeded product-level regression and multi-season stress checks."""

from copy import deepcopy
import random

from contracts import process_contracts
from data import CLUBS, SQUADS, get_best_starting_xi
from league import create_league_table
from progression import process_end_of_season
from stats import create_player_statistics
from transfer import buy_player, format_money


def test_ai_lineup_uses_the_transferred_player_from_career_state():
    squads = deepcopy(SQUADS)
    player = squads["Manchester City"][0]
    player["overall"] = 99
    success, _, _ = buy_player(
        squads, "Coventry City", player["name"], 500_000_000
    )

    assert success
    assert player in get_best_starting_xi("Coventry City", squads)
    assert player not in get_best_starting_xi("Manchester City", squads)


def test_money_display_is_compact_for_fees_but_exact_for_wages():
    assert format_money(42_500_000) == "£42.5m"
    assert format_money(85_000) == "£85,000"


def test_five_season_stress_preserves_clubs_squad_floor_and_unique_ids():
    squads = deepcopy(SQUADS)
    free_agents = []
    processed = set()
    history_seasons = []
    initial_ages = {p["id"]: p["age"] for squad in squads.values() for p in squad}

    for season in range(1, 6):
        stats = create_player_statistics(squads["Arsenal"])
        summary = process_end_of_season(
            squads, "Arsenal", stats, create_league_table(CLUBS), processed,
            season, random.Random(100 + season), free_agents=free_agents,
        )
        assert summary is not None
        history_seasons.append(season)

    active = [player for squad in squads.values() for player in squad]
    active_ids = [player["id"] for player in active]
    assert set(squads) == set(CLUBS)
    assert all(len(squad) >= 11 for squad in squads.values())
    assert all(player.get("id") for player in active)
    assert len(active_ids) == len(set(active_ids))
    assert all(1 <= player["contract_years"] <= 5 for player in active)
    assert history_seasons == [1, 2, 3, 4, 5]
    surviving = [player for player in active if player["id"] in initial_ages]
    assert all(player["age"] == initial_ages[player["id"]] + 5 for player in surviving)


def test_contract_processing_is_idempotent_with_academy_safety_net():
    squads = deepcopy(SQUADS)
    for squad in squads.values():
        for player in squad:
            player["contract_years"] = 1
    free_agents = []
    processed = set()

    first = process_contracts(squads, free_agents, 1, processed)
    snapshot = [(club, [p["id"] for p in squad]) for club, squad in squads.items()]

    assert first
    assert process_contracts(squads, free_agents, 1, processed) is None
    assert snapshot == [(club, [p["id"] for p in squad]) for club, squad in squads.items()]
    assert all(len(squad) == 11 for squad in squads.values())
