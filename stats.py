"""Player goals and season-statistics helpers."""

import random

from discipline import availability_status

POSITION_SCORING_WEIGHTS = {
    "ST": 10,
    "LW": 7,
    "RW": 7,
    "CAM": 7,
    "CM": 4,
    "LB": 1.5,
    "RB": 1.5,
    "CB": 1,
    "GK": 0.05,
}


def create_player_statistics(squad):
    """Create empty season totals for every player in a squad."""
    # Card keys are added on first use, keeping older saved statistics compatible.
    return {player["name"]: {"appearances": 0, "goals": 0} for player in squad}


def reset_player_statistics(squad):
    """Start new appearance and goal totals for the current squad."""
    return create_player_statistics(squad)


def ensure_player_statistics(statistics, squad):
    """Give newly signed players their own empty totals."""
    for player in squad:
        totals = statistics.setdefault(player["name"], {})
        for key in ("appearances", "goals"):
            totals.setdefault(key, 0)
    return statistics


def assign_goalscorers(starting_xi, goal_count, rng=None):
    """Assign each goal to a starter and return chronological goal events."""
    random_generator = rng or random
    weights = [
        POSITION_SCORING_WEIGHTS.get(player["position"], 1)
        * (1 + max(0, player["overall"] - 60) / 100)
        for player in starting_xi
    ]
    scorers = random_generator.choices(starting_xi, weights=weights, k=goal_count)
    events = [
        {"player": player["name"], "minute": random_generator.randint(1, 90)}
        for player in scorers
    ]
    return sorted(events, key=lambda event: event["minute"])


def record_match_statistics(
    statistics, starting_xi, goal_events, gameweek, recorded_gameweeks, card_events=None
):
    """Record a completed match once, including appearances and goals."""
    if gameweek in recorded_gameweeks:
        return False

    ensure_player_statistics(statistics, starting_xi)
    for player in starting_xi:
        statistics[player["name"]]["appearances"] += 1
    for event in goal_events:
        statistics[event["player"]]["goals"] += 1
    for event in card_events or []:
        key = "yellow_cards" if event["type"] == "yellow" else "red_cards"
        statistics[event["player"]].setdefault(key, 0)
        statistics[event["player"]][key] += 1
    recorded_gameweeks.add(gameweek)
    return True


def get_current_squad_statistics(squad, statistics, sort_by="Goals"):
    """Return display rows for current squad members only."""
    ensure_player_statistics(statistics, squad)
    rows = [
        {
            "Player": player["name"],
            "Position": player["position"],
            "Age": player["age"],
            "Overall": player["overall"],
            "Fitness": player.get("fitness", 100),
            "Availability": availability_status(player),
            "Potential": player["potential"],
            "Wage": f"£{player['wage']:,}/week",
            "Contract": f"{player['contract_years']} year(s)",
            "Appearances": statistics[player["name"]]["appearances"],
            "Goals": statistics[player["name"]]["goals"],
            "Yellow Cards": statistics[player["name"]].get("yellow_cards", 0),
            "Red Cards": statistics[player["name"]].get("red_cards", 0),
        }
        for player in squad
    ]
    if sort_by in {"Goals", "Appearances", "Overall"}:
        rows.sort(key=lambda row: (-row[sort_by], row["Player"]))
    else:
        rows.sort(key=lambda row: row["Player"])
    return rows
