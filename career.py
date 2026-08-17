"""Career history and new-season transition helpers."""

import random

from discipline import reset_discipline_for_new_season
from fixtures import generate_fixtures
from fitness import reset_health_for_new_season
from league import create_league_table
from morale import reset_morale_form_for_new_season
from stats import reset_player_statistics
from squad_management import reset_squad_management_for_new_season
from transfer_offers import handle_new_season_offers
from scouting import remove_invalid_assignments


def record_season_history(history, season_number, summary):
    """Store one completed-season summary without creating duplicates."""
    if any(entry["season"] == season_number for entry in history):
        return False
    history.append(
        {
            "season": season_number,
            "champion": summary["champion"],
            "user_position": summary["user_position"],
            "top_scorer": summary["top_scorer"],
            "top_scorer_goals": summary["top_scorer_goals"],
        }
    )
    return True


def start_next_season(state, clubs, rng=None):
    """Reset season-only state while preserving the manager's career."""
    finished_season = state["season_number"]
    if finished_season not in state["processed_seasons"]:
        raise ValueError("Finish the current season before starting the next one.")

    # Transfers, player development and the budget live in career state and stay put.
    state["season_number"] = finished_season + 1
    state["fixtures"] = generate_fixtures(clubs, rng or random)
    state["league_table"] = create_league_table(clubs)
    state["current_gameweek"] = 1
    state["completed_gameweeks"] = set()
    state["recorded_stat_gameweeks"] = set()
    state["processed_health_gameweeks"] = set()
    state["processed_discipline_gameweeks"] = set()
    state["processed_morale_gameweeks"] = set()
    state["processed_offer_gameweeks"] = set()
    state["processed_scouting_gameweeks"] = set()
    remove_invalid_assignments(
        state.setdefault("scouting_assignments", []), state["career_squads"],
        state.setdefault("free_agents", []),
    )
    handle_new_season_offers(state.setdefault("transfer_offers", []))
    reset_health_for_new_season(state["career_squads"][state["active_club"]])
    reset_discipline_for_new_season(state["career_squads"][state["active_club"]])
    reset_morale_form_for_new_season(state["career_squads"][state["active_club"]])
    reset_squad_management_for_new_season(
        state["career_squads"][state["active_club"]]
    )
    state["player_statistics"] = reset_player_statistics(
        state["career_squads"][state["active_club"]]
    )
    state.pop("season_summary", None)
    state.pop("gameweek_results", None)
    return state
