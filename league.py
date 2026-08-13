"""Beginner-friendly league table logic for the manager game."""


def create_league_table(clubs):
    """Create a fresh table row with zero statistics for every club."""
    table = {}
    for club in clubs:
        table[club] = {
            "Played": 0,
            "Won": 0,
            "Drawn": 0,
            "Lost": 0,
            "Goals For": 0,
            "Goals Against": 0,
            "Goal Difference": 0,
            "Points": 0,
        }
    return table


def update_league_table(table, home_club, away_club, home_goals, away_goals):
    """Update both clubs in a league table after one match."""
    home_row = table[home_club]
    away_row = table[away_club]

    home_row["Played"] += 1
    away_row["Played"] += 1
    home_row["Goals For"] += home_goals
    home_row["Goals Against"] += away_goals
    away_row["Goals For"] += away_goals
    away_row["Goals Against"] += home_goals

    if home_goals > away_goals:
        home_row["Won"] += 1
        home_row["Points"] += 3
        away_row["Lost"] += 1
    elif away_goals > home_goals:
        away_row["Won"] += 1
        away_row["Points"] += 3
        home_row["Lost"] += 1
    else:
        home_row["Drawn"] += 1
        away_row["Drawn"] += 1
        home_row["Points"] += 1
        away_row["Points"] += 1

    # Recalculate this value from the goal totals so it always stays accurate.
    home_row["Goal Difference"] = home_row["Goals For"] - home_row["Goals Against"]
    away_row["Goal Difference"] = away_row["Goals For"] - away_row["Goals Against"]


def get_sorted_league_table(table):
    """Return display rows ordered by points, goal difference, then goals scored."""
    rows = [{"Club": club, **statistics} for club, statistics in table.items()]
    return sorted(
        rows,
        key=lambda row: (
            -row["Points"],
            -row["Goal Difference"],
            -row["Goals For"],
            row["Club"],
        ),
    )
