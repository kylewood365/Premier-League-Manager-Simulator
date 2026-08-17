"""Card, dismissal and suspension rules for league matches."""

import random


DEFENSIVE_POSITIONS = {"RB", "LB", "CB", "CM", "DM", "CDM"}
RED_CARD_STRENGTH_FACTOR = 0.88


def ensure_player_discipline(player):
    """Add discipline state to players created before this feature existed."""
    player.setdefault("league_yellow_cards", 0)
    player.setdefault("suspension_matches", 0)
    return player


def availability_status(player):
    """Describe all reasons why a player cannot currently be selected."""
    ensure_player_discipline(player)
    reasons = []
    if player.get("injured", False):
        reasons.append(f"Injured ({player.get('injury_gameweeks', 0)} GW)")
    if player["suspension_matches"] > 0:
        reasons.append(f"Suspended ({player['suspension_matches']} match(es))")
    return " and ".join(reasons) if reasons else "Available"


def red_card_strength(strength, red_cards):
    """Apply a noticeable, but not ruinous, penalty for each dismissal."""
    return strength * (RED_CARD_STRENGTH_FACTOR ** red_cards)


def _card_chance(player):
    return 0.13 if player.get("position") in DEFENSIVE_POSITIONS else 0.09


def simulate_player_cards(first_half_players, second_half_players=None, rng=None):
    """Generate realistic card events only while players are on the pitch.

    Starters who are replaced can only be booked in the first half, and players
    who come on can only receive a second-half card. A dismissed player receives
    no later events.
    """
    rng = rng or random
    second_half_players = list(second_half_players or first_half_players)
    first_names = {player["name"] for player in first_half_players}
    second_names = {player["name"] for player in second_half_players}
    players = {player["name"]: player for player in first_half_players + second_half_players}
    candidates = []
    for name, player in players.items():
        halves = []
        if name in first_names:
            halves.append((1, 45))
        if name in second_names:
            halves.append((46, 90))
        for start, end in halves:
            # Half-sized probabilities keep full-match totals modest.
            if rng.random() < _card_chance(player) / 2:
                candidates.append({"player": name, "minute": rng.randint(start, end), "type": "yellow"})
            if rng.random() < 0.004:
                candidates.append({"player": name, "minute": rng.randint(start, end), "type": "straight_red"})

    events = []
    yellow_counts = {}
    dismissed = set()
    for card in sorted(candidates, key=lambda event: event["minute"]):
        name = card["player"]
        if name in dismissed:
            continue
        if card["type"] == "straight_red":
            card["type"] = "red"
            card["reason"] = "straight red"
            dismissed.add(name)
            events.append(card)
            continue
        yellow_counts[name] = yellow_counts.get(name, 0) + 1
        events.append(card)
        if yellow_counts[name] == 2:
            events.append({
                "player": name, "minute": card["minute"], "type": "red",
                "reason": "second yellow",
            })
            dismissed.add(name)
    return sorted(events, key=lambda event: (event["minute"], event["type"] == "red"))


def apply_discipline_events(squad, events):
    """Update card accumulation and create bans, returning newly banned names."""
    by_name = {player["name"]: player for player in squad}
    newly_suspended = set()
    for event in events:
        player = by_name.get(event["player"])
        if player is None:
            continue
        ensure_player_discipline(player)
        if event["type"] == "yellow":
            player["league_yellow_cards"] += 1
            if player["league_yellow_cards"] >= 5:
                player["league_yellow_cards"] -= 5
                player["suspension_matches"] += 1
                newly_suspended.add(player["name"])
        elif event["type"] == "red":
            ban = 1 if event.get("reason") == "second yellow" else 3
            player["suspension_matches"] += ban
            newly_suspended.add(player["name"])
    return newly_suspended


def process_suspensions(squad, gameweek, processed_gameweeks, newly_suspended=None):
    """Serve one match of existing bans exactly once after a league gameweek."""
    if gameweek in processed_gameweeks:
        return {"recoveries": [], "processed": False}
    newly_suspended = set(newly_suspended or [])
    recoveries = []
    for player in squad:
        ensure_player_discipline(player)
        if player["name"] in newly_suspended or player["suspension_matches"] <= 0:
            continue
        player["suspension_matches"] -= 1
        if player["suspension_matches"] == 0:
            recoveries.append(player["name"])
    processed_gameweeks.add(gameweek)
    return {"recoveries": recoveries, "processed": True}


def reset_discipline_for_new_season(squad):
    """Clear league accumulation and active bans for a fresh season."""
    for player in squad:
        ensure_player_discipline(player)
        player["league_yellow_cards"] = 0
        player["suspension_matches"] = 0
