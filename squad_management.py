"""Squad roles, playing-time expectations and transfer-request rules."""

import random

from morale import clamp_morale, ensure_player_morale_form


SQUAD_ROLES = (
    "Star Player", "Important Player", "Regular Starter", "Squad Player", "Prospect"
)
ROLE_EXPECTATIONS = {
    "Star Player": 0.80,
    "Important Player": 0.65,
    "Regular Starter": 0.50,
    "Squad Player": 0.25,
    "Prospect": 0.10,
}


def satisfaction_label(value):
    """Turn the internal satisfaction score into a clear status."""
    if value >= 85:
        return "Very Happy"
    if value >= 70:
        return "Happy"
    if value >= 50:
        return "Content"
    if value >= 30:
        return "Unhappy"
    return "Very Unhappy"


def sensible_role(player, squad=None):
    """Choose a predictable role from age and relative squad quality."""
    if player.get("age", 30) <= 21 and player.get("overall", 0) < 75:
        return "Prospect"
    ratings = sorted((p["overall"] for p in (squad or [player])), reverse=True)
    rank = sum(rating > player["overall"] for rating in ratings)
    size = len(ratings)
    if rank < max(1, round(size * 0.13)):
        return "Star Player"
    if rank < max(2, round(size * 0.33)):
        return "Important Player"
    if rank < max(3, round(size * 0.67)):
        return "Regular Starter"
    return "Squad Player"


def ensure_squad_management(player, role=None, squad=None):
    """Add compatible squad-management state to a player record."""
    ensure_player_morale_form(player)
    chosen = player.get("squad_role", role or sensible_role(player, squad))
    player["squad_role"] = chosen if chosen in SQUAD_ROLES else "Squad Player"
    player.setdefault("role_satisfaction", 60)
    player.setdefault("available_league_games", 0)
    player.setdefault("participated_league_games", 0)
    player.setdefault("playing_time_history", [])
    player.setdefault("very_unhappy_weeks", 0)
    player.setdefault("transfer_requested", False)
    player.setdefault("transfer_listed", False)
    player.setdefault("playing_time_promise", None)
    player.setdefault("last_squad_management_gameweek", None)
    return player


def assign_default_roles(squad):
    """Assign initial roles to a whole squad using one consistent ranking."""
    for player in squad:
        # Explicitly calculate again for a fresh career, rather than retaining AI state.
        player["squad_role"] = sensible_role(player, squad)
        ensure_squad_management(player, squad=squad)
    return squad


def change_squad_role(player, role):
    """Change expectations without wiping the player's existing feelings."""
    if role not in SQUAD_ROLES:
        raise ValueError("Choose a valid Squad Role.")
    ensure_squad_management(player)
    player["squad_role"] = role
    return player


def process_playing_time(squad, participants, gameweek, rng=None, available_names=None):
    """Record one league match and gradually update satisfaction and morale."""
    participant_names = {p["name"] if isinstance(p, dict) else p for p in participants}
    rng = rng or random
    notifications = []
    for player in squad:
        ensure_squad_management(player, squad=squad)
        if player["last_squad_management_gameweek"] == gameweek:
            continue
        player["last_squad_management_gameweek"] = gameweek
        available = (
            player["name"] in available_names if available_names is not None
            else not player.get("injured", False) and player.get("suspension_matches", 0) <= 0
        )
        appeared = player["name"] in participant_names
        if not available and not appeared:
            continue
        player["available_league_games"] += 1
        player["participated_league_games"] += int(appeared)
        history = player["playing_time_history"]
        history.append(int(appeared))
        del history[:-5]

        ratio = sum(history) / len(history)
        gap = ratio - ROLE_EXPECTATIONS[player["squad_role"]]
        change = 2 if gap >= 0.15 else 1 if gap >= 0 else -2 if gap <= -0.35 else -1
        player["role_satisfaction"] = max(0, min(100, player["role_satisfaction"] + change))
        # Satisfaction remains a gentle influence beside the existing morale rules.
        if change < 0 and player["role_satisfaction"] < 50:
            player["morale"] = clamp_morale(player["morale"] - 1)
        elif change > 0 and player["role_satisfaction"] >= 70:
            player["morale"] = clamp_morale(player["morale"] + 1)

        promise = player.get("playing_time_promise")
        if promise and promise["active"]:
            promise["games_elapsed"] += 1
            promise["appearances"] += int(appeared)
            if promise["games_elapsed"] >= promise["length"]:
                promise["active"] = False
                promise["outcome"] = "fulfilled" if promise["appearances"] >= 3 else "failed"
                if promise["outcome"] == "fulfilled":
                    player["morale"] = clamp_morale(player["morale"] + 6)
                    player["role_satisfaction"] = min(100, player["role_satisfaction"] + 8)
                    player["transfer_requested"] = False
                else:
                    player["morale"] = clamp_morale(player["morale"] - 6)

        if satisfaction_label(player["role_satisfaction"]) == "Very Unhappy":
            player["very_unhappy_weeks"] += 1
        else:
            player["very_unhappy_weeks"] = max(0, player["very_unhappy_weeks"] - 1)
        if (not player["transfer_requested"] and player["very_unhappy_weeks"] >= 3
                and rng.random() < (0.55 if player["morale"] < 35 else 0.30)):
            player["transfer_requested"] = True
            notifications.append({"player": player["name"], "reason": "Unhappy with playing time."})
    return notifications


def promise_more_playing_time(player, length=5):
    """Make a five-game playing-time promise in response to a request."""
    ensure_squad_management(player)
    player["playing_time_promise"] = {
        "active": True, "length": length, "games_elapsed": 0, "appearances": 0,
        "outcome": None,
    }
    player["morale"] = clamp_morale(player["morale"] + 3)
    return player["playing_time_promise"]


def accept_transfer_request(player):
    """Accept a request and make the player available for sale."""
    ensure_squad_management(player)
    if not player["transfer_requested"]:
        return False
    player["transfer_listed"] = True
    return True


def set_transfer_listed(player, listed=True):
    """Let the manager list or unlist any player manually."""
    ensure_squad_management(player)
    player["transfer_listed"] = bool(listed)
    return player["transfer_listed"]


def reset_squad_management_for_new_season(squad):
    """Clear season playing-time totals while preserving roles and requests."""
    for player in squad:
        ensure_squad_management(player, squad=squad)
        player["available_league_games"] = 0
        player["participated_league_games"] = 0
        player["playing_time_history"] = []
        player["last_squad_management_gameweek"] = None
        if player["playing_time_promise"] and not player["playing_time_promise"]["active"]:
            player["playing_time_promise"] = None
