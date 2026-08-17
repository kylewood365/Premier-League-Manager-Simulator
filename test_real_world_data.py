"""Tests for the read-only API-Football integration (all HTTP is mocked)."""

from unittest.mock import Mock, patch

import pytest

import real_world_data as real


def test_api_key_comes_from_streamlit_secrets():
    with patch.object(real.st, "secrets", {"API_FOOTBALL_KEY": "configured-key"}):
        assert real._api_key() == "configured-key"


def test_missing_key_is_a_recoverable_error():
    with patch.object(real.st, "secrets", {}):
        with pytest.raises(real.RealWorldDataError, match="not configured"):
            real._api_key()


def test_team_parsing_ignores_malformed_rows():
    source = [
        {"team": {"id": 42, "name": "Arsenal"}},
        {"team": {"name": "No ID"}},
        None,
    ]
    assert real.parse_teams(source) == [{"team_id": 42, "name": "Arsenal"}]


def test_squad_parsing_preserves_ids_names_ages_and_normalizes_positions():
    source = [{"players": [
        {"id": 7, "name": "Example Player", "age": 24,
         "position": "Attacker", "number": 9},
        {"id": 8, "name": "Keeper", "age": None,
         "position": "Goalkeeper", "number": None},
        {"name": "Missing ID"}, None,
    ]}]
    players = real.parse_squad(source, 42, "Arsenal")
    assert players[0] == {
        "api_player_id": 7, "name": "Example Player", "age": 24,
        "api_position": "Attacker", "position": "FWD", "shirt_number": 9,
        "team_id": 42, "club": "Arsenal",
    }
    assert players[1]["position"] == "GK"
    assert players[1]["age"] is None


@pytest.mark.parametrize("source, expected", [
    ("Defender", "DEF"), ("Midfielder", "MID"), ("Forward", "FWD"),
    (None, "Unknown"), ("unexpected", "Unknown"),
])
def test_position_normalization(source, expected):
    assert real.normalize_position(source) == expected


def test_request_uses_header_and_handles_http_failure():
    response = Mock(status_code=503)
    response.raise_for_status.side_effect = real.requests.HTTPError("outage")
    with patch.object(real.requests, "get", return_value=response) as get:
        with pytest.raises(real.RealWorldDataError, match="temporarily unavailable"):
            real._request("/teams", {}, "secret")
    assert get.call_args.kwargs["headers"] == {"x-apisports-key": "secret"}


def test_rate_limit_and_empty_response_are_friendly_errors():
    limited = Mock(status_code=429)
    with patch.object(real.requests, "get", return_value=limited):
        with pytest.raises(real.RealWorldDataError, match="request limit"):
            real._request("/teams", {}, "secret")

    empty = Mock(status_code=200)
    empty.raise_for_status.return_value = None
    empty.json.return_value = {"response": []}
    with patch.object(real.requests, "get", return_value=empty):
        with pytest.raises(real.RealWorldDataError, match="no data"):
            real._request("/teams", {}, "secret")


def api_response(errors):
    response = Mock(status_code=200)
    response.raise_for_status.return_value = None
    response.json.return_value = {"errors": errors, "response": []}
    return response


@pytest.mark.parametrize("errors, expected", [
    ({"plan": "This season is not available on your plan"},
     "does not allow this season on the current subscription"),
    ({"token": "Error/Missing application key"},
     "rejected the configured API key"),
    ({"requests": "Daily request quota reached"},
     "request quota has been reached"),
    ({"parameters": "Invalid league id"},
     "API-Football error: parameters: Invalid league id"),
])
def test_api_error_categories(errors, expected):
    with patch.object(real.requests, "get", return_value=api_response(errors)):
        with pytest.raises(real.RealWorldDataError, match=expected):
            real._request("/teams", {}, "configured-secret")


def test_nested_and_list_errors_are_concise_and_readable():
    errors = {"parameters": {"season": ["Invalid", "Unavailable"]}}
    assert real.format_api_errors(errors) == (
        "parameters.season: Invalid; parameters.season: Unavailable"
    )


def test_credentials_are_never_in_displayed_api_errors():
    secret = "super-secret-api-key"
    errors = {
        "debug": f"Rejected credential {secret}",
        "access_token": "other-token-value",
    }
    with patch.object(real.requests, "get", return_value=api_response(errors)):
        with pytest.raises(real.RealWorldDataError) as raised:
            real._request("/teams", {}, secret)
    message = str(raised.value)
    assert secret not in message
    assert "other-token-value" not in message
    assert "raw response" not in message


def test_current_season_and_cached_account_diagnostic():
    assert real.CURRENT_SEASON == 2026
    rows = [{"league": {"id": 39}}]
    with patch.object(real, "_request", return_value=rows) as request:
        assert real._cached_season_diagnostic.__wrapped__("configured-secret")
    request.assert_called_once_with(
        "/leagues", {"id": 39, "season": 2026}, "configured-secret"
    )


def test_season_diagnostic_reports_unavailable_season():
    with patch.object(real, "_request", return_value=[{"league": {"id": 2}}]):
        with pytest.raises(real.RealWorldDataError, match="season 2026 is unavailable"):
            real._cached_season_diagnostic.__wrapped__("configured-secret")

def test_cached_helpers_have_twenty_four_hour_ttl_and_public_calls_reuse_them():
    assert real.CACHE_TTL_SECONDS == 86400
    with patch.object(real, "_api_key", return_value="secret"), patch.object(
        real, "_cached_season_diagnostic", return_value=True
    ) as diagnostic, patch.object(
        real, "_cached_teams", return_value=[{"team_id": 1, "name": "Club"}]
    ) as cached:
        assert real.get_premier_league_teams()[0]["name"] == "Club"
        diagnostic.assert_called_once_with("secret")
        cached.assert_called_once_with("secret")


def test_player_statistics_pagination_fetches_exact_pages_and_combines():
    pages = {
        1: ([{"player": {"id": 1}, "statistics": [{"games": {"appearences": 2}}]}], {"total": 2}),
        2: ([{"player": {"id": 2}, "statistics": [{"games": {"minutes": 90}}]}], {"total": 2}),
    }
    with patch.object(real, "_request_page", side_effect=lambda path, params, key: pages[params["page"]]) as request:
        result = real._cached_player_statistics.__wrapped__("configured-secret")
    assert [row["api_player_id"] for row in result] == [1, 2]
    assert request.call_count == 2
    assert all(call.args[2] == "configured-secret" for call in request.call_args_list)


def test_statistics_join_is_by_id_and_keeps_missing_players():
    squad = [{"api_player_id": 1, "name": "Same"}, {"api_player_id": 2, "name": "Same"}]
    joined = real.join_squad_statistics(squad, [{"api_player_id": 2, "goals": 4}])
    assert joined[0]["statistics"] == {}
    assert joined[1]["statistics"]["goals"] == 4
