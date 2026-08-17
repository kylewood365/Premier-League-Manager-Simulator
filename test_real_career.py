"""Real career snapshot and lifecycle tests; no external API calls are made."""

from copy import deepcopy
import random
from unittest.mock import patch

import pytest

from budgets import career_budget_mappings
from career import start_next_season
from contracts import calculate_wage_spend, renew_contract
from fixtures import generate_fixtures
from game import simulate_gameweek
from league import create_league_table
from real_career import (
    build_real_career_snapshot, build_real_career_squads, create_real_career_player,
    validate_real_career_squads,
)
from real_world_data import RealWorldDataError
from stats import create_player_statistics
from tactics import can_field_formation, validate_starting_xi
from transfer import buy_player, sign_free_agent
from transfer_offers import accept_offer


def api_player(api_id, club, position):
    return {
        "api_player_id": api_id, "name": f"Player {api_id}", "age": 24,
        "position": position, "api_position": position,
        "shirt_number": api_id % 30 + 1, "club": club, "statistics": {},
    }


def mocked_api_league(size=20, players_per_club=16):
    teams = [{"team_id": index, "name": f"API Club {index}"} for index in range(size)]
    squads = {}
    positions = ["GK"] + ["DEF"] * 6 + ["MID"] * 5 + ["FWD"] * 4
    for team in teams:
        squads[team["team_id"]] = [
            api_player(team["team_id"] * 100 + n, team["name"], positions[n % len(positions)])
            for n in range(players_per_club)
        ]
    return teams, squads


def build_mocked(size=20, players_per_club=16):
    teams, squads = mocked_api_league(size, players_per_club)
    with (
        patch("real_career.get_real_data_source", return_value=("full", teams)),
        patch("real_career.get_current_squad", side_effect=lambda team_id, _club, paced=False: squads[team_id]),
        patch("real_career.get_premier_league_player_statistics", return_value=[]),
    ):
        return build_real_career_squads()


def test_real_builder_uses_api_membership_and_creates_complete_independent_players():
    squads = build_mocked()
    assert list(squads) == [f"API Club {n}" for n in range(20)]
    assert len({p["api_player_id"] for squad in squads.values() for p in squad}) == 320
    required = {
        "id", "api_player_id", "name", "age", "position", "api_position",
        "shirt_number", "club", "overall", "potential", "value", "wage",
        "contract_years", "fitness", "injured", "injury_gameweeks",
        "suspension_matches", "morale", "recent_form", "squad_role",
    }
    player = squads["API Club 0"][0]
    assert required <= player.keys()
    assert player["id"] == "api-player-0"
    assert player["value"] > 0 and player["wage"] > 0
    assert player["fitness"] == 100 and player["morale"] == 75
    assert player["contract_years"] == 4


def test_real_snapshot_validation_is_atomic_and_strict():
    with pytest.raises(RealWorldDataError, match="exactly 20"):
        build_mocked(size=19)
    with pytest.raises(RealWorldDataError, match="11 usable"):
        build_mocked(players_per_club=10)


def test_seasonless_snapshot_skips_statistics_and_paces_current_squads():
    teams, squads = mocked_api_league()
    calls = []
    with patch("real_career.get_real_data_source", return_value=("seasonless", teams)), patch(
        "real_career.get_premier_league_player_statistics", side_effect=AssertionError
    ), patch("real_career.get_current_squad", side_effect=lambda team_id, club, paced=False:
             calls.append((team_id, club, paced)) or squads[team_id]):
        snapshot, mode = build_real_career_snapshot()
    assert mode == "seasonless" and len(snapshot) == 20
    assert len(calls) == 20 and all(call[2] for call in calls)
    assert snapshot["API Club 0"][0]["id"] == "api-player-0"


def test_full_snapshot_preserves_statistics_path():
    teams, squads = mocked_api_league()
    with patch("real_career.get_real_data_source", return_value=("full", teams)), patch(
        "real_career.get_premier_league_player_statistics", return_value=[]
    ) as statistics, patch("real_career.get_current_squad",
                           side_effect=lambda team_id, _club, paced=False: squads[team_id]):
        snapshot, mode = build_real_career_snapshot()
    assert mode == "full" and len(snapshot) == 20
    statistics.assert_called_once_with()


def test_broad_positions_field_xi_and_fictional_specific_positions_still_work():
    squad = build_mocked()["API Club 0"]
    assert can_field_formation(squad, "4-3-3")
    broad_xi = [squad[0], *squad[1:5], *squad[7:10], *squad[12:15]]
    assert validate_starting_xi(broad_xi, "4-3-3")
    specific = [
        {"name": str(i), "position": pos}
        for i, pos in enumerate(["GK", "RB", "CB", "CB", "LB", "CM", "CM", "CAM", "RW", "LW", "ST"])
    ]
    assert validate_starting_xi(specific, "4-3-3")


def test_api_only_clubs_get_budgets_fixtures_and_table():
    squads = build_mocked()
    transfers, wages = career_budget_mappings(squads)
    assert all(value > 0 for value in transfers.values())
    assert all(value > 0 for value in wages.values())
    fixtures = generate_fixtures(list(squads))
    assert len(fixtures) == 38 and all(len(week) == 10 for week in fixtures)
    assert set(create_league_table(list(squads))) == set(squads)


def test_adapter_maps_preview_finance_names_to_career_names():
    player = create_real_career_player(api_player(12345, "Promoted FC", "FWD"))
    assert player["id"] == "api-player-12345"
    assert "transfer_value" not in player and "weekly_wage" not in player
    assert player["value"] > 0 and player["wage"] > 0


def test_career_player_is_an_independent_mutable_snapshot():
    source = api_player(12345, "Source FC", "MID")
    original = deepcopy(source)
    career_player = create_real_career_player(source)
    career_player.update(club="Career FC", overall=1, contract_years=1, fitness=2)
    assert source == original


def test_mocked_real_career_end_to_end_transfers_finance_and_next_season():
    squads = build_mocked()
    clubs = list(squads)
    source_snapshot = deepcopy(squads)
    managed, seller, buyer = clubs[:3]
    fixtures = generate_fixtures(clubs, random.Random(7))
    table = create_league_table(clubs)
    transfers, wages = career_budget_mappings(squads)
    xi = [squads[managed][0], *squads[managed][1:5], *squads[managed][7:10],
          *squads[managed][12:15]]
    statistics = create_player_statistics(squads[managed])

    assert len(clubs) == 20 and all(len(squad) >= 11 for squad in squads.values())
    assert len(fixtures) == 38 and len(fixtures[0]) == 10
    assert set(table) == set(clubs) and validate_starting_xi(xi, "4-3-3")
    assert all(totals == {"appearances": 0, "goals": 0} for totals in statistics.values())
    results = simulate_gameweek(
        1, fixtures, managed, xi, table, set(), random.Random(8), statistics,
        set(), squads[managed], set(), career_squads=squads,
    )
    assert len(results) == 10 and all(row["Played"] == 1 for row in table.values())
    assert sum(row["appearances"] for row in statistics.values()) == 11

    target = squads[seller][0]
    identity = target["id"], target["api_player_id"]
    affordable_budget = max(transfers[managed], target["value"])
    assert buy_player(squads, managed, target["name"], affordable_budget)[0]
    assert (target["id"], target["api_player_id"], target["club"]) == (*identity, managed)
    assert not buy_player(squads, managed, squads[seller][0]["name"], 0)[0]

    outgoing = target
    offer = {"id": 1, "player": outgoing["name"], "buying_club": buyer,
             "offered_fee": outgoing["value"], "status": "Pending"}
    transfers[buyer] = max(transfers[buyer], outgoing["value"])
    history = []
    assert accept_offer(offer, squads, managed, transfers, history)[0]
    assert (outgoing["id"], outgoing["api_player_id"], outgoing["club"]) == (*identity, buyer)
    assert history[-1]["from_club"] == managed and history[-1]["to_club"] == buyer

    free_agent = squads[seller].pop()
    free_agent["club"] = None
    free_agents = [free_agent]
    wage_budget = calculate_wage_spend(squads[managed]) + free_agent["wage"]
    assert sign_free_agent(squads, managed, free_agents, free_agent["name"], 2,
                           wage_budget, history)[0]
    assert free_agent["club"] == managed
    renewal_player = squads[managed][0]
    renewal_player["contract_years"] = 1
    assert renew_contract(renewal_player, 1, squads[managed], 10_000_000)[0]

    state = {
        "season_number": 1, "processed_seasons": {1}, "career_clubs": clubs,
        "career_squads": squads, "active_club": managed, "free_agents": [],
    }
    ids_and_clubs = {(p["id"], p.get("api_player_id")): club
                     for club, squad in squads.items() for p in squad}
    with (patch("real_career.get_real_data_source", side_effect=AssertionError),
          patch("real_career.get_current_squad", side_effect=AssertionError),
          patch("real_career.get_premier_league_player_statistics", side_effect=AssertionError)):
        start_next_season(state, state["career_clubs"], random.Random(9))
    assert state["career_clubs"] == clubs and len(state["fixtures"]) == 38
    assert set(state["league_table"]) == set(clubs)
    assert ids_and_clubs == {(p["id"], p.get("api_player_id")): club
                             for club, squad in squads.items() for p in squad}
    assert source_snapshot != squads
