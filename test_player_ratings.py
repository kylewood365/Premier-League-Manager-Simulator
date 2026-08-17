"""Unit tests for simulator-owned real-player rating estimates."""

from player_ratings import calculate_overall, calculate_potential, create_simulator_player


def player(position="FWD", age=24):
    return {"api_player_id": 123, "name": "Test Player", "age": age,
            "position": position, "api_position": "Attacker", "shirt_number": 9,
            "club": "Test Club"}


def test_ratings_are_deterministic_bounded_and_no_stats_are_valid():
    assert calculate_overall(player(), {}) == calculate_overall(player(), {})
    assert 55 <= calculate_overall(player(), {}) <= 94
    record = create_simulator_player(player(), {})
    assert record["transfer_value"] > 0 and record["weekly_wage"] > 0
    assert record["id"] == "api-player-123" and record["api_player_id"] == 123


def test_potential_bounds_and_youth_headroom():
    young = calculate_potential(70, 19)
    old = calculate_potential(70, 31)
    assert young - 70 > old - 70
    assert young >= 70 and calculate_potential(93, 18) == 94


def test_position_specific_performance_and_small_sample_protection():
    season = {"minutes": 1800, "appearances": 24, "average_match_rating": 7.2}
    assert calculate_overall(player("FWD"), {**season, "goals": 15, "assists": 8}) > calculate_overall(player("FWD"), season)
    assert calculate_overall(player("DEF"), {**season, "tackles": 70, "interceptions": 40}) > calculate_overall(player("DEF"), season)
    assert calculate_overall(player("GK"), {**season, "saves": 90, "clean_sheets": 10}) > calculate_overall(player("GK"), season)
    tiny = calculate_overall(player(), {"minutes": 30, "appearances": 1, "goals": 1, "average_match_rating": 10})
    assert tiny < 80
