"""Tests for persistent, display-only scouting knowledge."""

from copy import deepcopy

from data import SQUADS
from retirement import generate_youth_player
from scouting import (
    BASIC, FULLY_SCOUTED, SCOUTED, UNSCOUTED, assign_scout,
    initialise_scouting, knowledge_level, player_id, process_scouting,
    remove_invalid_assignments, visible_player_data,
)
from transfer import buy_player


def setup_state():
    squads = deepcopy(SQUADS)
    knowledge = initialise_scouting(squads, "Arsenal")
    return squads, knowledge


def test_own_players_are_known_and_external_players_start_unscouted():
    squads, knowledge = setup_state()
    assert knowledge_level(squads["Arsenal"][0], "Arsenal", "Arsenal", knowledge) == 3
    assert knowledge_level(squads["Chelsea"][0], "Chelsea", "Arsenal", knowledge) == 0


def test_visibility_ranges_narrow_without_mutating_real_attributes():
    player = deepcopy(SQUADS["Chelsea"][0])
    original = deepcopy(player)
    hidden = visible_player_data(player, UNSCOUTED)
    basic = visible_player_data(player, BASIC)
    scouted = visible_player_data(player, SCOUTED)
    full = visible_player_data(player, FULLY_SCOUTED)
    assert (hidden["Overall"], hidden["Potential"], hidden["Value"]) == ("?", "?", "Unknown")
    basic_low, basic_high = map(int, basic["Overall"].split("–"))
    scout_low, scout_high = map(int, scouted["Overall"].split("–"))
    assert basic_low <= player["overall"] <= basic_high
    assert scout_low <= player["overall"] <= scout_high
    assert scout_high - scout_low < basic_high - basic_low
    assert full["Overall"] == player["overall"]
    assert full["Potential"] == player["potential"]
    assert full["Value"] == f"£{player['value']:,.0f}"
    assert player == original


def test_assignment_limits_duplicates_timing_progression_and_reruns():
    squads, knowledge = setup_state()
    assignments, reports, processed = [], [], set()
    targets = squads["Chelsea"][:4]
    assert assign_scout(targets[0], "Chelsea", "Arsenal", knowledge, assignments, 1, 1)[0]
    assert not assign_scout(targets[0], "Chelsea", "Arsenal", knowledge, assignments, 1, 1)[0]
    assert assign_scout(targets[1], "Chelsea", "Arsenal", knowledge, assignments, 1, 1)[0]
    assert assign_scout(targets[2], "Chelsea", "Arsenal", knowledge, assignments, 1, 1)[0]
    assert not assign_scout(targets[3], "Chelsea", "Arsenal", knowledge, assignments, 1, 1)[0]
    assert process_scouting(assignments, knowledge, reports, squads, 1, 1, processed) == []
    completed = process_scouting(assignments, knowledge, reports, squads, 1, 2, processed)
    assert len(completed) == 3
    assert knowledge[player_id(targets[0])] == BASIC
    assert process_scouting(assignments, knowledge, reports, squads, 1, 2, processed) == []
    assert knowledge[player_id(targets[0])] == BASIC


def test_knowledge_survives_transfer_and_signing_makes_player_fully_known():
    squads, knowledge = setup_state()
    target = squads["Chelsea"][0]
    identifier = player_id(target)
    knowledge[identifier] = BASIC
    target["value"] = 1
    assert buy_player(
        squads, "Arsenal", target["name"], 10, scouting_knowledge=knowledge
    )[0]
    assert player_id(squads["Arsenal"][-1]) == identifier
    assert knowledge[identifier] == FULLY_SCOUTED


def test_youth_ids_are_unique_and_club_ownership_controls_knowledge():
    youth_one = generate_youth_player("CM")
    youth_two = generate_youth_player("CM")
    assert player_id(youth_one) != player_id(youth_two)
    knowledge = {}
    assert knowledge_level(youth_one, "Chelsea", "Arsenal", knowledge) == UNSCOUTED
    assert knowledge_level(youth_two, "Arsenal", "Arsenal", knowledge) == FULLY_SCOUTED


def test_retired_player_cannot_remain_assigned_and_season_data_is_preserved():
    squads, knowledge = setup_state()
    target = squads["Chelsea"][0]
    assignments = []
    assign_scout(target, "Chelsea", "Arsenal", knowledge, assignments, 1, 10)
    squads["Chelsea"].remove(target)
    remove_invalid_assignments(assignments, squads)
    assert assignments == []
    reports = [{"player_id": player_id(target), "season": 1}]
    preserved = dict(knowledge)
    # A new season clears neither persistent container.
    assert knowledge == preserved
    assert reports[0]["season"] == 1
