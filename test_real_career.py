"""Real career snapshot tests; no external API calls are made."""

from unittest.mock import patch

import pytest

from budgets import career_budget_mappings
from fixtures import generate_fixtures
from league import create_league_table
from real_career import (
    build_real_career_squads, create_real_career_player,
    validate_real_career_squads,
)
from real_world_data import RealWorldDataError
from tactics import can_field_formation, validate_starting_xi


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
        patch("real_career.get_premier_league_teams", return_value=teams),
        patch("real_career.get_current_squad", side_effect=lambda team_id, _club: squads[team_id]),
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
