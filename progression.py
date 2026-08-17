"""End-of-season player development and aging rules."""

import random

from data import calculate_player_value
from league import get_sorted_league_table
from retirement import process_retirements
from contracts import age_free_agents, process_contracts

ATTACKING_POSITIONS = {"ST", "LW", "RW", "CAM"}


def calculate_overall_change(player, statistics, rng=None):
    """Return this season's small rating change for one player.

    Appearances give young players opportunities to fulfil their potential, while
    goals provide a modest extra boost to attacking players. Older players have
    an increasingly high chance of declining.
    """
    rng = rng or random
    age = player["age"]
    overall = player["overall"]
    potential = player["potential"]
    appearances = statistics.get("appearances", 0)
    goals = statistics.get("goals", 0)

    if age >= 30:
        decline_chance = min(0.85, 0.25 + (age - 30) * 0.10)
        if rng.random() < decline_chance:
            return -2 if age >= 34 and rng.random() < 0.45 else -1
        return 0

    room = potential - overall
    if room <= 0:
        return 0

    age_chance = 0.55 if age <= 21 else 0.38 if age <= 24 else 0.20
    appearance_bonus = min(appearances, 38) / 38 * (0.35 if age <= 24 else 0.20)
    goal_bonus = 0
    if player["position"] in ATTACKING_POSITIONS:
        goal_bonus = min(goals, 20) / 20 * 0.12
    if rng.random() >= min(0.95, age_chance + appearance_bonus + goal_bonus):
        return 0

    improvement = 1
    if appearances >= 24 and age <= 24 and room >= 2 and rng.random() < 0.55:
        improvement += 1
    if appearances >= 32 and age <= 21 and room >= 3 and rng.random() < 0.30:
        improvement += 1
    return min(improvement, room, 3)


def develop_player(player, statistics, rng=None):
    """Apply and return a player's rating change, within the allowed limits."""
    old_overall = player["overall"]
    change = calculate_overall_change(player, statistics, rng)
    player["overall"] = max(50, min(player["potential"], old_overall + change))
    return player["overall"] - old_overall


def get_league_champion(league_table):
    """Return the champion using the same tie-breakers as the displayed table."""
    rows = get_sorted_league_table(league_table)
    return rows[0]["Club"] if rows else None


def process_end_of_season(
    squads, user_club, player_statistics, league_table, processed_seasons,
    season=1, rng=None, retirement_history=None, free_agents=None
):
    """Progress the user's squad and age the whole league exactly once per season."""
    if season in processed_seasons:
        return None

    rng = rng or random
    summary = []
    for player in squads[user_club]:
        old_overall = player["overall"]
        stats = player_statistics.get(player["name"], {"appearances": 0, "goals": 0})
        develop_player(player, stats, rng)
        if player["overall"] != old_overall:
            summary.append({
                "player": player["name"],
                "old_overall": old_overall,
                "new_overall": player["overall"],
                "change": player["overall"] - old_overall,
            })

    # Every player ages, including players at AI-controlled clubs. Revaluing after
    # both rating movement and aging keeps the transfer market internally consistent.
    for squad in squads.values():
        for player in squad:
            player["age"] += 1
            player["value"] = calculate_player_value(player["overall"], player["age"])

    # Retirement follows development and aging. A replacement is inserted into
    # the same list immediately, so no club ever loses the ability to field an XI.
    retirement_history = retirement_history if retirement_history is not None else []
    # Retirees leave football before expiring contracts are moved to free agency.
    retirements = process_retirements(squads, season, retirement_history, None, rng)
    free_agents = free_agents if free_agents is not None else []
    age_free_agents(free_agents)
    contract_events = process_contracts(squads, free_agents, season, processed_seasons)

    sorted_table = get_sorted_league_table(league_table)
    user_position = next(
        index for index, row in enumerate(sorted_table, 1) if row["Club"] == user_club
    )
    top_scorer, top_stats = max(
        player_statistics.items(), key=lambda item: (item[1]["goals"], item[0])
    )
    result = {
        "champion": get_league_champion(league_table),
        "user_position": user_position,
        "top_scorer": top_scorer,
        "top_scorer_goals": top_stats["goals"],
        "development": summary,
        "retirements": retirements,
        "contract_events": contract_events,
    }
    return result
