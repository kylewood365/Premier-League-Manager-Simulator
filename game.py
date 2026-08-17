"""Simple match simulation logic for the manager game."""

import math
import random

from data import calculate_team_strength, get_best_starting_xi
from discipline import (
    apply_discipline_events, process_suspensions, red_card_strength,
    simulate_player_cards,
)
from fitness import process_gameweek_health
from league import update_league_table
from morale import process_match_morale_and_form
from squad_management import process_playing_time
from stats import assign_goalscorers, record_match_statistics
from tactics import apply_substitutions, tactical_strength, validate_bench, validate_starting_xi


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


def _expected_goals(home_strength, away_strength, home_style, away_style):
    """Calculate full-match scoring rates with modest tactical adjustments."""
    home_attack, home_defence = tactical_strength(home_strength, home_style)
    away_attack, away_defence = tactical_strength(away_strength, away_style)
    home_difference = (home_attack + 2) - away_defence
    away_difference = away_attack - (home_defence + 2)
    return (
        min(3.5, max(0.25, 1.35 + home_difference * 0.045)),
        min(3.5, max(0.25, 1.15 + away_difference * 0.045)),
    )


def simulate_half(home_strength, away_strength, home_style="Balanced", away_style="Balanced", rng=None):
    """Simulate one half, allowing a changed team and tactic after half-time."""
    random_generator = rng or random
    home_xg, away_xg = _expected_goals(home_strength, away_strength, home_style, away_style)
    return {
        "home_score": _score_goals(home_xg / 2, random_generator),
        "away_score": _score_goals(away_xg / 2, random_generator),
    }


def simulate_match(home_club, away_club, home_strength, away_strength, rng=None,
                   home_style="Balanced", away_style="Balanced"):
    """Simulate one match, including a small advantage for the home club."""
    random_generator = rng or random

    first = simulate_half(home_strength, away_strength, home_style, away_style, random_generator)
    second = simulate_half(home_strength, away_strength, home_style, away_style, random_generator)
    home_score = first["home_score"] + second["home_score"]
    away_score = first["away_score"] + second["away_score"]

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
        "first_half_home_score": first["home_score"],
        "first_half_away_score": first["away_score"],
        "second_half_home_score": second["home_score"],
        "second_half_away_score": second["away_score"],
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
    user_squad=None,
    processed_health_gameweeks=None,
    formation="4-3-3",
    tactical_style="Balanced",
    bench=None,
    substitutions=None,
    first_half_result=None,
    processed_discipline_gameweeks=None,
    processed_morale_gameweeks=None,
):
    """Play all ten matches in a gameweek and update the table once."""
    if gameweek_number in completed_gameweeks:
        raise ValueError("This gameweek has already been completed.")
    if not 1 <= gameweek_number <= len(fixtures):
        raise ValueError("Invalid gameweek number.")
    validate_starting_xi(user_starting_xi, formation)
    bench = bench or []
    substitutions = substitutions or []
    validate_bench(bench, user_starting_xi)
    second_half_xi = apply_substitutions(user_starting_xi, bench, substitutions)
    available_at_kickoff = {
        player["name"] for player in (user_squad or [])
        if not player.get("injured", False) and player.get("suspension_matches", 0) <= 0
    }

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
        is_user_match = user_club in (fixture["home"], fixture["away"])
        if is_user_match:
            second_strength = calculate_team_strength(second_half_xi)
            card_events = simulate_player_cards(user_starting_xi, second_half_xi, rng)
            first_half_user_reds = sum(
                event["type"] == "red" and event["minute"] <= 45
                for event in card_events
            )
            second_strength = red_card_strength(second_strength, first_half_user_reds)
            # AI clubs only need a team-level dismissal in this first version.
            opponent_first_half_reds = int((rng or random).random() < 0.015)
            home_strength = second_strength if fixture["home"] == user_club else strengths[fixture["home"]]
            away_strength = second_strength if fixture["away"] == user_club else strengths[fixture["away"]]
            if fixture["home"] != user_club:
                home_strength = red_card_strength(home_strength, opponent_first_half_reds)
            else:
                away_strength = red_card_strength(away_strength, opponent_first_half_reds)
            home_style = tactical_style if fixture["home"] == user_club else "Balanced"
            away_style = tactical_style if fixture["away"] == user_club else "Balanced"
            if first_half_result is None:
                first_half_result = simulate_half(
                    strengths[fixture["home"]], strengths[fixture["away"]],
                    home_style, away_style, rng,
                )
            second = simulate_half(home_strength, away_strength, home_style, away_style, rng)
            match = simulate_match(fixture["home"], fixture["away"], home_strength, away_strength, rng)
            match.update({
                "first_half_home_score": first_half_result["home_score"],
                "first_half_away_score": first_half_result["away_score"],
                "second_half_home_score": second["home_score"],
                "second_half_away_score": second["away_score"],
                "home_score": first_half_result["home_score"] + second["home_score"],
                "away_score": first_half_result["away_score"] + second["away_score"],
            })
            if match["home_score"] > match["away_score"]:
                match.update(winner=match["home_club"], result=f"{match['home_club']} win")
            elif match["away_score"] > match["home_score"]:
                match.update(winner=match["away_club"], result=f"{match['away_club']} win")
            else:
                match.update(winner=None, result="Draw")
            match["user_score"] = match["home_score"]
            match["opponent_score"] = match["away_score"]
            match["card_events"] = card_events
            match["user_red_cards"] = sum(event["type"] == "red" for event in card_events)
            match["opponent_red_cards"] = opponent_first_half_reds
        else:
            home_style = tactical_style if fixture["home"] == user_club else "Balanced"
            away_style = tactical_style if fixture["away"] == user_club else "Balanced"
            match = simulate_match(fixture["home"], fixture["away"], strengths[fixture["home"]], strengths[fixture["away"]], rng, home_style, away_style)
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
            participants = user_starting_xi + [player for player in second_half_xi if player not in user_starting_xi]
            match["goal_events"] = assign_goalscorers(participants, user_goals, rng)
            if player_statistics is not None:
                record_match_statistics(
                    player_statistics,
                    participants,
                    match["goal_events"],
                    gameweek_number,
                    recorded_stat_gameweeks
                    if recorded_stat_gameweeks is not None
                    else completed_gameweeks,
                    match.get("card_events", []),
                )
        results.append(match)

    health_events = {"injuries": [], "recoveries": [], "processed": False}
    if user_squad is not None:
        health_events = process_gameweek_health(
            user_squad,
            user_starting_xi,
            gameweek_number,
            processed_health_gameweeks
            if processed_health_gameweeks is not None
            else completed_gameweeks,
            rng,
            substitutes=[player for player in second_half_xi if player not in user_starting_xi],
        )
        discipline_weeks = (
            processed_discipline_gameweeks
            if processed_discipline_gameweeks is not None else set()
        )
        if gameweek_number not in discipline_weeks:
            user_match = next(
                match for match in results
                if user_club in (match["home_club"], match["away_club"])
            )
            newly_suspended = apply_discipline_events(
                user_squad, user_match.get("card_events", [])
            )
            suspension_events = process_suspensions(
                user_squad, gameweek_number, discipline_weeks, newly_suspended
            )
            user_match["suspension_recovery_events"] = suspension_events["recoveries"]
        user_match = next(
            match for match in results
            if user_club in (match["home_club"], match["away_club"])
        )
        user_is_home = user_match["home_club"] == user_club
        user_score = user_match["home_score"] if user_is_home else user_match["away_score"]
        opponent_score = user_match["away_score"] if user_is_home else user_match["home_score"]
        if user_score > opponent_score:
            result = "win"
        elif user_score < opponent_score:
            result = "loss"
        else:
            result = "draw"
        entered = [player for player in second_half_xi if player not in user_starting_xi]
        request_events = process_playing_time(
            user_squad, user_starting_xi + entered, gameweek_number, rng,
            available_at_kickoff,
        )
        user_match["transfer_request_events"] = request_events
        process_match_morale_and_form(
            user_squad, user_starting_xi, entered, bench, result,
            user_match.get("goal_events", []), user_match.get("card_events", []),
            gameweek_number,
            processed_morale_gameweeks if processed_morale_gameweeks is not None else completed_gameweeks,
            health_events["injuries"], rng,
        )
    completed_gameweeks.add(gameweek_number)
    for match in results:
        if user_club in (match["home_club"], match["away_club"]):
            match["injury_events"] = health_events["injuries"]
            match["recovery_events"] = health_events["recoveries"]
    return results
