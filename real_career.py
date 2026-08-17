"""Build a one-time, independent real-squad career snapshot."""

from contracts import starting_contract_years
from discipline import ensure_player_discipline
from fitness import ensure_player_health
from morale import ensure_player_morale_form
from player_ratings import create_simulator_player
from real_world_data import (
    CURRENT_SEASON, RealWorldDataError, get_current_squad, get_real_data_source,
    get_premier_league_player_statistics, join_squad_statistics,
)
from squad_management import ensure_squad_management
from tactics import FORMATIONS, can_field_formation


def create_real_career_player(api_player):
    """Adapt a rated preview record to the mutable career-engine contract."""
    preview = create_simulator_player(api_player)
    age = preview["age"] if isinstance(preview["age"], int) else 25
    player = {
        "id": preview["id"], "api_player_id": preview["api_player_id"],
        "name": preview["name"], "age": age, "position": preview["position"],
        "api_position": preview["api_position"],
        "shirt_number": preview["shirt_number"], "club": preview["club"],
        "overall": preview["overall"], "potential": preview["potential"],
        "value": preview["transfer_value"], "wage": preview["weekly_wage"],
        "contract_years": starting_contract_years(age),
    }
    ensure_player_health(player)
    ensure_player_discipline(player)
    ensure_player_morale_form(player)
    ensure_squad_management(player)
    return player


def validate_real_career_squads(squads):
    """Reject incomplete API snapshots before any career state is changed."""
    if len(squads) != 20:
        raise RealWorldDataError("A Real Squads career requires exactly 20 Premier League clubs.")
    ids, api_ids = set(), set()
    for club, squad in squads.items():
        if len(squad) < 11:
            raise RealWorldDataError(f"{club} does not currently have 11 usable squad players.")
        for player in squad:
            player_id, api_id = player.get("id"), player.get("api_player_id")
            if not player_id or player_id in ids or not isinstance(api_id, int) or api_id in api_ids:
                raise RealWorldDataError("The API squad contains missing or duplicate player identities.")
            ids.add(player_id); api_ids.add(api_id)
            if not 1 <= player.get("overall", 0) <= 100 or not 1 <= player.get("potential", 0) <= 100:
                raise RealWorldDataError(f"{club} contains an invalid simulator rating.")
            if player.get("value", 0) <= 0 or player.get("wage", 0) <= 0:
                raise RealWorldDataError(f"{club} contains invalid simulator finances.")
        if not any(can_field_formation(squad, formation) for formation in FORMATIONS):
            raise RealWorldDataError(f"{club} cannot field a usable starting XI.")
    return True


def build_real_career_snapshot(progress=None):
    """Fetch and atomically prepare squads plus their frozen source mode."""
    mode, teams = get_real_data_source()
    statistics = get_premier_league_player_statistics() if mode == "full" else []
    squads = {}
    for index, team in enumerate(teams, 1):
        if progress:
            progress(team["name"], index, len(teams))
        raw = get_current_squad(
            team["team_id"], team["name"], paced=(mode == "seasonless")
        )
        squads[team["name"]] = [
            create_real_career_player(player)
            for player in join_squad_statistics(raw, statistics)
        ]
    validate_real_career_squads(squads)
    return squads, mode


def build_real_career_squads(progress=None):
    """Compatibility wrapper returning the mode-aware prepared squads."""
    return build_real_career_snapshot(progress)[0]


REAL_DATA_SEASON = CURRENT_SEASON
