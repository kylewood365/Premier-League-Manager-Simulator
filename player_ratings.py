"""Deterministic, simulator-owned estimates derived from real player data."""

from contracts import calculate_weekly_wage

MIN_OVERALL = 55
MAX_OVERALL = 94


def _n(stats, key):
    try:
        return max(0.0, float((stats or {}).get(key) or 0))
    except (TypeError, ValueError):
        return 0.0


def calculate_overall(player, statistics=None):
    """Estimate ability with position-specific production and sample protection."""
    s = statistics or player.get("statistics") or {}
    age = player.get("age") if isinstance(player.get("age"), int) else 25
    position = player.get("position", "Unknown")
    # Conservative deterministic prior; age only prevents identical empty records.
    prior = 64 + (2 if 22 <= age <= 29 else 0)
    minutes, apps = _n(s, "minutes"), _n(s, "appearances")
    confidence = min(1.0, minutes / 1500, apps / 18) if minutes and apps else 0
    rating = _n(s, "average_match_rating")
    rating_score = (rating - 6.0) * 10 if rating else 0
    per90 = 90 / max(minutes, 270)  # caps tiny-sample event rates
    if position == "GK":
        performance = rating_score + _n(s, "saves") * per90 * 1.4 + _n(s, "clean_sheets") * per90 * 3
    elif position == "DEF":
        performance = (rating_score + (_n(s, "tackles") + _n(s, "interceptions")) * per90 * .8
                       + _n(s, "clean_sheets") * per90 * 1.5
                       + (_n(s, "goals") + _n(s, "assists")) * per90 * 2)
    elif position == "MID":
        performance = (rating_score + _n(s, "assists") * per90 * 4 + _n(s, "goals") * per90 * 3
                       + _n(s, "passes") * per90 * .012
                       + (_n(s, "tackles") + _n(s, "interceptions")) * per90 * .25)
    else:
        performance = (rating_score + _n(s, "goals") * per90 * 5 + _n(s, "assists") * per90 * 3.5
                       + _n(s, "shots") * per90 * .35)
    # Even extraordinary full-season production reaches elite levels gradually.
    estimate = prior + max(-9, min(27, performance))
    overall = round(prior * (1 - confidence) + estimate * confidence)
    return max(MIN_OVERALL, min(MAX_OVERALL, overall))


def calculate_potential(overall, age):
    """Simulator estimate of headroom, based mainly on age and current ability."""
    age = age if isinstance(age, int) else 25
    headroom = 10 if age <= 20 else 6 if age <= 24 else 3 if age <= 28 else 1
    return min(MAX_OVERALL, max(overall, overall + headroom))


def calculate_transfer_value(overall, potential, age):
    """Extend the project's ability valuation with a potential premium."""
    age = age if isinstance(age, int) else 25
    ability = max(overall - 60, 1) * 2_000_000
    youth = max(0, 27 - age) * 1_000_000
    potential_premium = max(0, potential - overall) * 1_250_000
    return int(max(500_000, ability + youth + potential_premium))


def create_simulator_player(player, statistics=None):
    """Convert a read-only API squad player to a complete preview record."""
    stats = statistics if statistics is not None else player.get("statistics", {})
    overall = calculate_overall(player, stats)
    age = player.get("age") if isinstance(player.get("age"), int) else 25
    potential = calculate_potential(overall, age)
    api_id = player["api_player_id"]
    return {
        "id": f"api-player-{api_id}", "api_player_id": api_id,
        "name": player.get("name", "Unknown Player"), "age": player.get("age"),
        "position": player.get("position", "Unknown"),
        "api_position": player.get("api_position"),
        "shirt_number": player.get("shirt_number"), "club": player.get("club"),
        "overall": overall, "potential": potential,
        "transfer_value": calculate_transfer_value(overall, potential, age),
        "weekly_wage": calculate_weekly_wage(overall, age, potential),
    }
