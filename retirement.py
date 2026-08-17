"""End-of-season retirement and youth-player generation.

The functions in this module do not depend on Streamlit, which keeps the rules
easy to test and lets ``app.py`` concentrate on presenting their results.
"""

import random

from data import calculate_player_value


# Deliberately fictional combinations rather than names of current footballers.
YOUTH_FIRST_NAMES = [
    "Ethan", "Callum", "Milo", "Owen", "Theo", "Isaac", "Jude", "Ellis",
    "Noah", "Felix", "Arlo", "Reuben", "Kian", "Toby", "Nico",
]
YOUTH_SURNAMES = [
    "Clarke", "Meadow", "Hollis", "Pritchard", "Redfern", "Ainsworth",
    "Lennox", "Marlow", "Whitcombe", "Kersey", "Langford", "Fairbairn",
    "Bramwell", "Sayer", "Thornley",
]


def retirement_probability(age):
    """Return an older player's retirement chance after their birthday."""
    if age < 35:
        return 0.0
    if age >= 40:
        return 1.0
    return 0.15 + (age - 35) * 0.15


def should_retire(player, rng=None):
    """Decide whether a player retires using the age-based probability."""
    return (rng or random).random() < retirement_probability(player["age"])


def generate_youth_player(position, existing_names=(), rng=None):
    """Create a 16--19 year-old regen, normally with a unique squad name."""
    rng = rng or random
    existing_names = set(existing_names)
    choices = [
        f"{first} {surname}"
        for first in YOUTH_FIRST_NAMES
        for surname in YOUTH_SURNAMES
        if f"{first} {surname}" not in existing_names
    ]
    # Exhausting all 225 combinations is unlikely, but a suffix keeps names safe.
    name = rng.choice(choices) if choices else f"Youth Player {len(existing_names) + 1}"
    age = rng.randint(16, 19)
    overall = rng.randint(55, 72)
    potential = rng.randint(max(70, overall), 94)
    return {
        "name": name,
        "position": position,
        "age": age,
        "overall": overall,
        "potential": potential,
        "value": calculate_player_value(overall, age),
    }


def process_retirements(
    squads, season, retirement_history, processed_seasons=None, rng=None
):
    """Retire eligible players and immediately replace each at the same club.

    ``processed_seasons`` is optional for convenient standalone use. Career code
    supplies it so a Streamlit rerun cannot process the same season twice.
    """
    if processed_seasons is not None and season in processed_seasons:
        return None

    rng = rng or random
    events = []
    for club, squad in squads.items():
        retiring = [player for player in list(squad) if should_retire(player, rng)]
        for player in retiring:
            squad.remove(player)
            youth = generate_youth_player(
                player["position"], (member["name"] for member in squad), rng
            )
            squad.append(youth)
            record = {
                "player": player["name"],
                "club": club,
                "retirement_age": player["age"],
                "season": season,
            }
            retirement_history.append(record)
            events.append({**record, "youth": youth})

    if processed_seasons is not None:
        processed_seasons.add(season)
    return events
