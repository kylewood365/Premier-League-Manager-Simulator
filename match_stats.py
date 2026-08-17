"""Believable, score-aware statistics for the user's league matches."""

import random

from tactics import statistical_style


def _clamp(value, low, high):
    return max(low, min(high, value))


def generate_half_statistics(home_strength, away_strength, home_goals, away_goals,
                             home_style="Balanced", away_style="Balanced",
                             home_red_cards=0, away_red_cards=0, rng=None):
    """Generate one half around an authoritative score (never alter that score)."""
    generator = rng or random
    home_tactic = statistical_style(home_style)
    away_tactic = statistical_style(away_style)
    strength_gap = home_strength - away_strength

    home_possession = round(_clamp(
        50 + strength_gap * 0.32 + home_tactic["possession"]
        - away_tactic["possession"] - home_red_cards * 8 + away_red_cards * 8
        + generator.gauss(0, 3.5), 25, 75
    ))
    away_possession = 100 - home_possession

    def attacking(team_strength, opponent_strength, possession, tactic,
                  opponent_tactic, reds, opponent_reds, goals):
        expected_shots = (
            5.2 + (team_strength - opponent_strength) * 0.075
            + (possession - 50) * 0.045 + tactic["shots"] / 2
            + opponent_tactic["opponent"] / 2 - reds * 1.8 + opponent_reds * 1.3
        )
        shots = max(goals, round(_clamp(generator.gauss(expected_shots, 1.8), 1, 15)))
        accuracy = _clamp(
            0.37 + (team_strength - 75) * 0.0025 + tactic["quality"]
            + generator.gauss(0, 0.055), 0.25, 0.60
        )
        on_target = max(goals, min(shots, round(shots * accuracy)))
        quality = _clamp(
            0.105 + (team_strength - opponent_strength) * 0.0018
            + tactic["quality"] + opponent_reds * 0.018, 0.055, 0.24
        )
        xg = round(max(0.0, _clamp(
            shots * quality + generator.gauss(0, 0.13), 0.05, 2.4
        )), 2)
        return {"shots": shots, "shots_on_target": on_target, "xg": xg}

    home = attacking(home_strength, away_strength, home_possession, home_tactic,
                     away_tactic, home_red_cards, away_red_cards, home_goals)
    away = attacking(away_strength, home_strength, away_possession, away_tactic,
                     home_tactic, away_red_cards, home_red_cards, away_goals)
    home["possession"] = home_possession
    away["possession"] = away_possession
    return {"home": home, "away": away}


def combine_half_statistics(first_half, second_half):
    """Combine immutable half figures into full-match totals."""
    result = {}
    for side in ("home", "away"):
        result[side] = {
            "possession": round((first_half[side]["possession"] + second_half[side]["possession"]) / 2),
            "shots": first_half[side]["shots"] + second_half[side]["shots"],
            "shots_on_target": first_half[side]["shots_on_target"] + second_half[side]["shots_on_target"],
            "xg": round(first_half[side]["xg"] + second_half[side]["xg"], 2),
        }
    # Independent rounding can only be one point out; make the invariant exact.
    result["away"]["possession"] = 100 - result["home"]["possession"]
    return result


def create_history_record(season, gameweek, user_club, match):
    """Convert the completed user match into its compact season-history row."""
    home = match["home_club"] == user_club
    side, other = ("home", "away") if home else ("away", "home")
    stats = match["match_stats"]
    return {
        "season": season, "gameweek": gameweek,
        "opponent": match["away_club"] if home else match["home_club"],
        "home_away": "Home" if home else "Away",
        "score": f"{match[side + '_score']}-{match[other + '_score']}",
        "goals": match[side + "_score"],
        "possession": stats[side]["possession"], "shots": stats[side]["shots"],
        "shots_on_target": stats[side]["shots_on_target"], "xg": stats[side]["xg"],
    }


def record_match_history(history, record):
    """Append once per season/gameweek, preserving completed statistics on reruns."""
    if any(row["season"] == record["season"] and row["gameweek"] == record["gameweek"] for row in history):
        return False
    history.append(record)
    return True


def calculate_season_aggregates(history, season):
    """Calculate user-team totals from only the requested season."""
    rows = [row for row in history if row["season"] == season]
    count = len(rows)
    return {
        "matches": count,
        "average_possession": round(sum(r["possession"] for r in rows) / count, 1) if count else 0.0,
        "total_shots": sum(r["shots"] for r in rows),
        "total_shots_on_target": sum(r["shots_on_target"] for r in rows),
        "total_xg": round(sum(r["xg"] for r in rows), 2),
        "total_goals": sum(r["goals"] for r in rows),
        "average_xg": round(sum(r["xg"] for r in rows) / count, 2) if count else 0.0,
    }
