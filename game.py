"""Simple match simulation logic for the manager game."""

import math
import random


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


def simulate_match(user_club, opponent, user_strength, opponent_strength, rng=None):
    """Simulate one home match and return the clubs, score, and outcome."""
    random_generator = rng or random

    # Each rating point changes the expected goals a little. The user's club
    # receives a small home boost, while the limits keep scorelines believable.
    strength_difference = (user_strength + 2) - opponent_strength
    user_expected_goals = min(3.5, max(0.25, 1.35 + strength_difference * 0.045))
    opponent_expected_goals = min(3.5, max(0.25, 1.15 - strength_difference * 0.045))

    user_score = _score_goals(user_expected_goals, random_generator)
    opponent_score = _score_goals(opponent_expected_goals, random_generator)

    if user_score > opponent_score:
        result = f"{user_club} win"
        winner = user_club
    elif opponent_score > user_score:
        result = f"{opponent} win"
        winner = opponent
    else:
        result = "Draw"
        winner = None

    return {
        "user_club": user_club,
        "opponent": opponent,
        "user_score": user_score,
        "opponent_score": opponent_score,
        "winner": winner,
        "result": result,
    }
