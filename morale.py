"""Player morale and recent league-form rules."""

import random


def clamp_morale(value):
    """Keep morale inside its public 0--100 range."""
    return max(0, min(100, int(round(value))))


def ensure_player_morale_form(player, rng=None, default_morale=None):
    """Add valid morale/form state to old saves and newly arriving players."""
    if default_morale is None:
        default_morale = (rng or random).randint(70, 80) if rng is not None else 75
    player["morale"] = clamp_morale(player.get("morale", default_morale))
    ratings = player.get("recent_form", [])
    player["recent_form"] = [round(float(rating), 1) for rating in ratings[-5:]]
    player.setdefault("consecutive_omissions", 0)
    return player


def morale_label(morale):
    """Return the manager-friendly description for a morale value."""
    morale = clamp_morale(morale)
    if morale >= 90:
        return "Excellent"
    if morale >= 75:
        return "Good"
    if morale >= 55:
        return "Okay"
    if morale >= 35:
        return "Low"
    return "Very Low"


def form_score(player):
    """Return average recent form, or None before a league appearance."""
    ensure_player_morale_form(player)
    ratings = player["recent_form"]
    return round(sum(ratings) / len(ratings), 1) if ratings else None


def form_label(score):
    """Describe a form average."""
    if score is None:
        return "N/A"
    if score >= 8.0:
        return "Excellent"
    if score >= 7.2:
        return "Good"
    if score >= 6.5:
        return "Average"
    return "Poor"


def add_form_rating(player, rating):
    """Append one appearance and retain only the latest five."""
    ensure_player_morale_form(player)
    player["recent_form"].append(round(max(6.0, min(10.0, rating)), 1))
    player["recent_form"] = player["recent_form"][-5:]


def calculate_match_rating(started=True, result="draw", goals=0, red_card=False):
    """Calculate a deliberately simple league appearance rating."""
    rating = 6.7 if started else 6.4
    rating += {"win": 0.5, "draw": 0.1, "loss": -0.3}.get(result, 0)
    rating += min(goals, 3) * 0.7
    if red_card:
        rating -= 1.0
    return round(max(6.0, min(10.0, rating)), 1)


def process_match_morale_and_form(
    squad, starters, substitutes, bench, result, goal_events, card_events,
    gameweek, processed_gameweeks, injury_events=None, rng=None,
):
    """Apply one match's changes once, including gradual selection unhappiness."""
    if gameweek in processed_gameweeks:
        return False
    rng = rng or random
    starter_names = {player["name"] for player in starters}
    substitute_names = {player["name"] for player in substitutes}
    bench_names = {player["name"] for player in bench}
    goals = {}
    for event in goal_events:
        goals[event["player"]] = goals.get(event["player"], 0) + 1
    reds = {event["player"] for event in card_events if event["type"] == "red"}
    injured = {event["player"] for event in (injury_events or [])}

    for player in squad:
        ensure_player_morale_form(player, rng)
        name = player["name"]
        appeared = name in starter_names or name in substitute_names
        change = 0
        if appeared:
            change += {"win": 2, "draw": 0, "loss": -2}[result]
            change += min(goals.get(name, 0), 2)
            change -= 2 if name in reds else 0
            change -= 1 if name in injured else 0
            player["consecutive_omissions"] = 0
            add_form_rating(player, calculate_match_rating(
                name in starter_names, result, goals.get(name, 0), name in reds
            ))
        elif name in bench_names:
            player["consecutive_omissions"] = player.get("consecutive_omissions", 0) + 1
            if rng.random() < 0.5:
                change -= 1
        elif not player.get("injured", False) and player.get("age", 0) >= 23:
            player["consecutive_omissions"] = player.get("consecutive_omissions", 0) + 1
            if player["consecutive_omissions"] >= 2:
                change -= 1
        player["morale"] = clamp_morale(player["morale"] + change)
    processed_gameweeks.add(gameweek)
    return True


def reset_morale_form_for_new_season(squad):
    """Clear form and gently pull extreme morale toward a neutral 72."""
    for player in squad:
        ensure_player_morale_form(player)
        player["morale"] = clamp_morale(player["morale"] + (72 - player["morale"]) * 0.25)
        player["recent_form"] = []
        player["consecutive_omissions"] = 0
