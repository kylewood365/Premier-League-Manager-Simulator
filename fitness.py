"""Player fitness and injury rules for the manager's squad.

The values live on each player dictionary so they naturally travel with players
during transfers.  AI teams are not processed each week in this first version.
"""

import random


INJURY_TYPES = ("hamstring injury", "ankle injury", "calf strain", "knee injury")


def ensure_player_health(player, default_fitness=100):
    """Add a valid health state to an older or newly-created player record."""
    player["fitness"] = max(0, min(100, player.get("fitness", default_fitness)))
    player.setdefault("injured", False)
    player.setdefault("injury_gameweeks", 0)
    if player["injury_gameweeks"] <= 0:
        player["injured"] = False
        player["injury_gameweeks"] = 0
    return player


def is_available(player):
    """Return whether a player is healthy and free to be selected."""
    ensure_player_health(player)
    return not player["injured"] and player.get("suspension_matches", 0) <= 0


def effective_rating(player):
    """Scale Overall from 50% at zero Fitness to 100% when fully fit."""
    ensure_player_health(player)
    fitness_multiplier = 0.5 + player["fitness"] / 200
    return player["overall"] * fitness_multiplier


def injury_chance(player):
    """Return a small risk which rises clearly as Fitness falls."""
    ensure_player_health(player)
    return 0.01 + (100 - player["fitness"]) * 0.001


def process_gameweek_health(
    squad, starters, gameweek, processed_gameweeks, rng=None, substitutes=None
):
    """Apply fatigue, recovery and injuries exactly once for a gameweek.

    Returns injury and recovery events for presentation by the UI.  A newly
    sustained injury keeps its full duration; pre-existing injuries tick down.
    """
    if gameweek in processed_gameweeks:
        return {"injuries": [], "recoveries": [], "processed": False}

    rng = rng or random
    for player in squad:
        ensure_player_health(player)

    starter_ids = {id(player) for player in starters}
    substitute_ids = {id(player) for player in (substitutes or [])}
    previously_injured = {
        id(player) for player in squad if player["injured"]
    }
    injuries = []

    for player in starters:
        ensure_player_health(player)
        # Veterans tend to lose one or two extra points, while the random base
        # keeps ordinary match fatigue around the requested 6--12 range.
        age_extra = max(0, (player["age"] - 29) // 4)
        player["fitness"] = max(0, player["fitness"] - rng.randint(6, 12) - age_extra)
        if not player["injured"] and rng.random() < injury_chance(player):
            player["injured"] = True
            player["injury_gameweeks"] = rng.randint(1, 6)
            injury_type = rng.choice(INJURY_TYPES)
            injuries.append({
                "player": player["name"],
                "injury": injury_type,
                "gameweeks": player["injury_gameweeks"],
            })

    # Players entering after kick-off do less work and therefore lose less fitness.
    for player in substitutes or []:
        ensure_player_health(player)
        player["fitness"] = max(0, player["fitness"] - rng.randint(3, 6))

    # Everyone gets normal between-match recovery, with rested players gaining
    # more. Starters still finish with a net loss in the usual case.
    for player in squad:
        if id(player) in starter_ids:
            recovery = rng.randint(2, 5)
        elif id(player) in substitute_ids:
            recovery = rng.randint(2, 5)
        else:
            recovery = rng.randint(7, 12)
        player["fitness"] = min(100, player["fitness"] + recovery)

    recoveries = []
    for player in squad:
        if id(player) not in previously_injured:
            continue
        player["injury_gameweeks"] = max(0, player["injury_gameweeks"] - 1)
        if player["injury_gameweeks"] == 0:
            player["injured"] = False
            recoveries.append(player["name"])

    processed_gameweeks.add(gameweek)
    return {"injuries": injuries, "recoveries": recoveries, "processed": True}


def reset_health_for_new_season(squad):
    """Begin a new season with every active player fully fit and healthy."""
    for player in squad:
        player.update({"fitness": 100, "injured": False, "injury_gameweeks": 0})
