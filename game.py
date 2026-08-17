"""Simple match simulation logic for the manager game."""

import math
import random

from data import calculate_team_strength, get_best_starting_xi
from league import update_league_table
from stats import assign_goalscorers, record_match_statistics


def _score_goals(expected_goals, random_generator):
    """Choose a goal total using a simple Poisson-style calculation."""
    # This loop produces mostly low scores, as real football matches do.
    limit = math.exp(-expected_goals)
    attempts = 0
    chance = 1.0
    while chance > limit:
        attempts += 1
        chance *= random_generator.random()
    return attempts - 1


def simulate_match(home_club, away_club, home_strength, away_strength, rng=None):
    """Simulate one match, including a small advantage for the home club."""
    random_generator = rng or random

    # Each rating point changes the expected goals a little. The user's club
    # receives a small home boost, while the limits keep scorelines believable.
    strength_difference = (home_strength + 2) - away_strength
    home_expected_goals = min(3.5, max(0.25, 1.35 + strength_difference * 0.045))
    away_expected_goals = min(3.5, max(0.25, 1.15 - strength_difference * 0.045))

    home_score = _score_goals(home_expected_goals, random_generator)
    away_score = _score_goals(away_expected_goals, random_generator)

    if home_score > away_score:
        result = f"{home_club} win"
        winner = home_club
    elif away_score > home_score:
        result = f"{away_club} win"
        winner = away_club
    else:
        result = "Draw"
        winner = None

    return {
        "home_club": home_club,
        "away_club": away_club,
        "home_score": home_score,
        "away_score": away_score,
        # These aliases keep the original single-match API compatible.
        "user_club": home_club,
        "opponent": away_club,
        "user_score": home_score,
        "opponent_score": away_score,
        "winner": winner,
        "result": result,
    }


def simulate_gameweek(
    gameweek_number,
    fixtures,
    user_club,
    user_starting_xi,
    table,
    completed_gameweeks,
    rng=None,
    player_statistics=None,
    recorded_stat_gameweeks=None,
):
    """Play all ten matches in a gameweek and update the table once."""
    if gameweek_number in completed_gameweeks:
        raise ValueError("This gameweek has already been completed.")
    if not 1 <= gameweek_number <= len(fixtures):
        raise ValueError("Invalid gameweek number.")

    user_strength = calculate_team_strength(user_starting_xi)
    strengths = {}
    for match in fixtures[gameweek_number - 1]:
        for club in (match["home"], match["away"]):
            strengths[club] = (
                user_strength
                if club == user_club
                else calculate_team_strength(get_best_starting_xi(club))
            )

    results = []
    for fixture in fixtures[gameweek_number - 1]:
        match = simulate_match(
            fixture["home"],
            fixture["away"],
            strengths[fixture["home"]],
            strengths[fixture["away"]],
            rng,
        )
        update_league_table(
            table,
            match["home_club"],
            match["away_club"],
            match["home_score"],
            match["away_score"],
        )
        if user_club in (match["home_club"], match["away_club"]):
            user_goals = (
                match["home_score"]
                if match["home_club"] == user_club
                else match["away_score"]
            )
            match["goal_events"] = assign_goalscorers(
                user_starting_xi, user_goals, rng
            )
            if player_statistics is not None:
                record_match_statistics(
                    player_statistics,
                    user_starting_xi,
                    match["goal_events"],
                    gameweek_number,
                    recorded_stat_gameweeks
                    if recorded_stat_gameweeks is not None
                    else completed_gameweeks,
                )
        results.append(match)

    completed_gameweeks.add(gameweek_number)
    return results
