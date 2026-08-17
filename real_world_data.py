"""Read-only access to current Premier League data from API-Football.

This module deliberately returns new, normalized dictionaries.  API responses
are never placed in the mutable fictional career squads.
"""

import requests
import streamlit as st


BASE_URL = "https://v3.football.api-sports.io"
PREMIER_LEAGUE_ID = 39
CURRENT_SEASON = 2026
CACHE_TTL_SECONDS = 24 * 60 * 60
REQUEST_TIMEOUT_SECONDS = 15


class RealWorldDataError(Exception):
    """A friendly, recoverable problem while loading real-world data."""


def _api_key():
    """Read the key at call time so importing the app never requires a secret."""
    try:
        key = st.secrets["API_FOOTBALL_KEY"]
    except (KeyError, FileNotFoundError):
        key = None
    if not key:
        raise RealWorldDataError(
            "API-Football is not configured. Add API_FOOTBALL_KEY to your "
            "Streamlit secrets to use the Real World Data preview."
        )
    return str(key)


def is_api_configured():
    """Report whether Real Squads can be offered as the default database."""
    try:
        return bool(st.secrets["API_FOOTBALL_KEY"])
    except (KeyError, FileNotFoundError):
        return False


def _request(path, params, api_key):
    """Make one API request and turn service failures into friendly errors."""
    try:
        response = requests.get(
            f"{BASE_URL}{path}", params=params,
            headers={"x-apisports-key": api_key}, timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code == 429:
            raise RealWorldDataError(
                "API-Football's request limit has been reached. Please try again later."
            )
        response.raise_for_status()
        payload = response.json()
    except RealWorldDataError:
        raise
    except (requests.RequestException, ValueError) as exc:
        raise RealWorldDataError(
            "API-Football is temporarily unavailable. Please try again later."
        ) from exc

    errors = payload.get("errors") if isinstance(payload, dict) else None
    if errors:
        raise RealWorldDataError(
            "API-Football could not complete the request. Please try again later."
        )
    rows = payload.get("response") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or not rows:
        raise RealWorldDataError("API-Football returned no data for this request.")
    return rows


def _request_page(path, params, api_key):
    """Return response rows and pagination for endpoints which paginate."""
    try:
        response = requests.get(
            f"{BASE_URL}{path}", params=params,
            headers={"x-apisports-key": api_key}, timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code == 429:
            raise RealWorldDataError(
                "API-Football's request limit has been reached. Please try again later."
            )
        response.raise_for_status()
        payload = response.json()
    except RealWorldDataError:
        raise
    except (requests.RequestException, ValueError) as exc:
        raise RealWorldDataError(
            "API-Football player statistics are temporarily unavailable."
        ) from exc
    if not isinstance(payload, dict) or payload.get("errors"):
        raise RealWorldDataError("API-Football returned malformed player statistics.")
    rows = payload.get("response")
    paging = payload.get("paging", payload.get("pagination", {}))
    if not isinstance(rows, list) or not isinstance(paging, dict):
        raise RealWorldDataError("API-Football returned malformed player statistics.")
    return rows, paging


def normalize_position(api_position):
    """Convert API-Football's broad positions to simulator positions."""
    position = str(api_position or "").strip().lower()
    return {
        "goalkeeper": "GK",
        "defender": "DEF",
        "midfielder": "MID",
        "attacker": "FWD",
        "forward": "FWD",
    }.get(position, "Unknown")


def parse_teams(rows):
    """Extract only the stable ID and name needed by the preview."""
    teams = []
    for row in rows or []:
        team = row.get("team", {}) if isinstance(row, dict) else {}
        team_id, name = team.get("id"), team.get("name")
        if isinstance(team_id, int) and name:
            teams.append({"team_id": team_id, "name": str(name)})
    return teams


def parse_squad(rows, team_id, club):
    """Create safe player records without mutating API response dictionaries."""
    players = []
    for row in rows or []:
        for player in row.get("players", []) if isinstance(row, dict) else []:
            if not isinstance(player, dict):
                continue
            api_player_id = player.get("id")
            name = player.get("name")
            if not isinstance(api_player_id, int) or not name:
                continue
            api_position = player.get("position")
            players.append({
                "api_player_id": api_player_id,
                "name": str(name),
                "age": player.get("age") if isinstance(player.get("age"), int) else None,
                "api_position": api_position,
                "position": normalize_position(api_position),
                "shirt_number": (
                    player.get("number") if isinstance(player.get("number"), int) else None
                ),
                "team_id": team_id,
                "club": club,
            })
    return players


def _number(value, default=0):
    """Coerce optional API numbers without allowing malformed values through."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_player_statistics(rows):
    """Flatten API-Football player responses into safe simulator inputs."""
    parsed = []
    for row in rows or []:
        if not isinstance(row, dict) or not isinstance(row.get("player"), dict):
            continue
        player = row["player"]
        player_id = player.get("id")
        if not isinstance(player_id, int):
            continue
        # The endpoint may include several competition/team statistic blocks.
        for stats in row.get("statistics", []) or []:
            if not isinstance(stats, dict):
                continue
            games = stats.get("games") or {}
            goals = stats.get("goals") or {}
            shots = stats.get("shots") or {}
            passes = stats.get("passes") or {}
            tackles = stats.get("tackles") or {}
            cards = stats.get("cards") or {}
            goalkeeper = stats.get("goals") or {}
            parsed.append({
                "api_player_id": player_id,
                "appearances": int(_number(games.get("appearences"))),
                "starts": int(_number(games.get("lineups"))),
                "minutes": int(_number(games.get("minutes"))),
                "average_match_rating": _number(games.get("rating"), None),
                "goals": int(_number(goals.get("total"))),
                "assists": int(_number(goals.get("assists"))),
                "shots": int(_number(shots.get("total"))),
                "passes": int(_number(passes.get("total"))),
                "tackles": int(_number(tackles.get("total"))),
                "interceptions": int(_number(tackles.get("interceptions"))),
                "saves": int(_number(goalkeeper.get("saves"))),
                "clean_sheets": int(_number(games.get("clean_sheets", stats.get("clean_sheet")))),
                "yellow_cards": int(_number(cards.get("yellow"))),
                "red_cards": int(_number(cards.get("red"))),
            })
    return parsed


def join_squad_statistics(squad, statistics):
    """Left-join statistics to a squad using only API player IDs."""
    by_id = {row["api_player_id"]: row for row in statistics or []
             if isinstance(row, dict) and isinstance(row.get("api_player_id"), int)}
    return [{**player, "statistics": dict(by_id.get(player["api_player_id"], {}))}
            for player in squad]


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def _cached_teams(api_key):
    rows = _request(
        "/teams", {"league": PREMIER_LEAGUE_ID, "season": CURRENT_SEASON}, api_key
    )
    teams = parse_teams(rows)
    if not teams:
        raise RealWorldDataError("No Premier League clubs were found.")
    return teams


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def _cached_squad(team_id, club, api_key):
    rows = _request("/players/squads", {"team": team_id}, api_key)
    players = parse_squad(rows, team_id, club)
    if not players:
        raise RealWorldDataError(f"No registered squad was found for {club}.")
    return players


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def _cached_player_statistics(api_key):
    """Fetch exactly the page count advertised by API-Football."""
    base = {"league": PREMIER_LEAGUE_ID, "season": CURRENT_SEASON}
    first, paging = _request_page("/players", {**base, "page": 1}, api_key)
    try:
        total = max(1, int(paging.get("total", 1)))
    except (TypeError, ValueError):
        raise RealWorldDataError("API-Football returned invalid pagination information.")
    rows = list(first)
    for page in range(2, total + 1):
        try:
            page_rows, _ = _request_page("/players", {**base, "page": page}, api_key)
        except RealWorldDataError as exc:
            raise RealWorldDataError(
                f"Player statistics page {page} could not be loaded. Basic squads remain available."
            ) from exc
        rows.extend(page_rows)
    return parse_player_statistics(rows)


def get_premier_league_teams():
    """Return the current Premier League clubs (normally cached for 24 hours)."""
    return _cached_teams(_api_key())


def get_current_squad(team_id, club=None):
    """Return one club's current registered squad."""
    club = club or f"Team {team_id}"
    return _cached_squad(int(team_id), club, _api_key())


def get_all_premier_league_squads():
    """Return squads keyed by club name, reusing the per-team 24-hour cache."""
    return {
        team["name"]: get_current_squad(team["team_id"], team["name"])
        for team in get_premier_league_teams()
    }


def get_premier_league_player_statistics():
    """Return all league player statistics, cached as one dataset for 24 hours."""
    return _cached_player_statistics(_api_key())


def get_squad_with_statistics(team_id, club=None):
    """Keep every registered player and attach statistics where available."""
    return join_squad_statistics(
        get_current_squad(team_id, club), get_premier_league_player_statistics()
    )
