"""Tests for the read-only manager dashboard summaries."""

from copy import deepcopy

from dashboard import (
    career_summary, club_form, financial_summary, initialise_navigation,
    next_fixture, recent_results, squad_status, top_players,
)
from data import SQUADS


def history_row(gameweek, opponent, venue, score):
    return {"season": 2, "gameweek": gameweek, "opponent": opponent,
            "home_away": venue, "score": score}


def test_next_fixture_uses_current_gameweek_and_table_position():
    fixtures = [
        [{"home": "Arsenal", "away": "Chelsea"}],
        [{"home": "Liverpool", "away": "Arsenal"}],
    ]
    table = {
        "Arsenal": {"Played": 1, "Won": 1, "Drawn": 0, "Lost": 0, "Goals For": 2,
                    "Goals Against": 0, "Goal Difference": 2, "Points": 3},
        "Chelsea": {"Played": 1, "Won": 0, "Drawn": 0, "Lost": 1, "Goals For": 0,
                    "Goals Against": 2, "Goal Difference": -2, "Points": 0},
        "Liverpool": {"Played": 1, "Won": 0, "Drawn": 1, "Lost": 0, "Goals For": 1,
                      "Goals Against": 1, "Goal Difference": 0, "Points": 1},
    }
    result = next_fixture(fixtures, 2, "Arsenal", table)
    assert result == {"gameweek": 2, "home": "Liverpool", "away": "Arsenal",
                      "opponent": "Liverpool", "venue": "Away", "opponent_position": 2}


def test_recent_results_returns_latest_five_and_form_is_chronological():
    history = [history_row(i, f"Club {i}", "Home" if i % 2 else "Away", score)
               for i, score in enumerate(("1-0", "0-1", "2-2", "3-1", "0-2", "1-0"), 1)]
    results = recent_results(history, 2, "Arsenal")
    assert [row["gameweek"] for row in results] == [6, 5, 4, 3, 2]
    assert club_form(history, 2, "Arsenal") == ["L", "D", "W", "L", "W"]
    assert results[0]["home_team"] == "Club 6"
    assert results[0]["away_team"] == "Arsenal"


def test_squad_status_counts_health_discipline_and_requests():
    squad = deepcopy(SQUADS["Arsenal"][:4])
    squad[0].update(injured=True, injury_gameweeks=2)
    squad[1]["suspension_matches"] = 1
    squad[2]["morale"] = 40
    squad[3]["transfer_requested"] = True
    assert squad_status(squad) == {"squad_size": 4, "available": 2, "injured": 1,
                                   "suspended": 1, "unhappy": 1, "transfer_requests": 1}


def test_top_players_and_finances_use_current_squad_values():
    squad = deepcopy(SQUADS["Arsenal"][:3])
    squad[0]["recent_ratings"] = [8.4, 8.0]
    squad[1]["recent_ratings"] = [6.1]
    stats = {p["name"]: {"appearances": 2, "goals": index} for index, p in enumerate(squad)}
    leaders = top_players(squad, stats)
    assert leaders["top_scorer"][0]["name"] == squad[2]["name"]
    assert leaders["top_scorer"][1] == 2
    assert leaders["best_form"][0]["name"] == squad[0]["name"]
    finances = financial_summary(squad, 25_000_000, 1_000_000)
    assert finances["wage_spend"] == sum(player["wage"] for player in squad)
    assert finances["wage_remaining"] == 1_000_000 - finances["wage_spend"]


def test_career_summary_and_empty_history_are_safe():
    assert career_summary([], "Arsenal") == {"seasons_completed": 0, "best_finish": None, "titles": 0}
    history = [{"user_position": 4, "champion": "Chelsea"},
               {"user_position": 1, "champion": "Arsenal"}]
    assert career_summary(history, "Arsenal") == {"seasons_completed": 2, "best_finish": 1, "titles": 1}


def test_navigation_initialisation_preserves_career_state():
    state = {"active_club": "Arsenal", "season_number": 3, "current_gameweek": 14}
    snapshot = dict(state)
    assert initialise_navigation(state) == "Dashboard"
    assert {key: state[key] for key in snapshot} == snapshot
    state["navigation"] = "League"
    assert initialise_navigation(state) == "League"
