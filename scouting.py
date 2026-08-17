"""Scouting knowledge and reports, separate from real player data."""

import uuid

UNSCOUTED = 0
BASIC = 1
SCOUTED = 2
FULLY_SCOUTED = 3
KNOWLEDGE_NAMES = ["Unscouted", "Basic Knowledge", "Scouted", "Fully Scouted"]
MAX_ACTIVE_ASSIGNMENTS = 3


def player_id(player):
    """Return a stable identifier, adding one for old save data when necessary."""
    if not player.get("id"):
        player["id"] = f"player-{uuid.uuid4().hex}"
    return player["id"]


def initialise_scouting(squads, user_club, knowledge=None):
    """Add IDs and initialise knowledge without overwriting saved discoveries."""
    knowledge = knowledge if knowledge is not None else {}
    for club, squad in squads.items():
        for player in squad:
            knowledge.setdefault(
                player_id(player), FULLY_SCOUTED if club == user_club else UNSCOUTED
            )
    return knowledge


def knowledge_level(player, club, user_club, knowledge):
    """The manager always knows their own players, regardless of saved state."""
    if club == user_club:
        return FULLY_SCOUTED
    return knowledge.get(player_id(player), UNSCOUTED)


def _number_range(value, margin, minimum=0, maximum=None):
    low = max(minimum, value - margin)
    high = value + margin
    if maximum is not None:
        high = min(maximum, high)
    return f"{low}–{high}"


def _money_range(value, percentage):
    million = 1_000_000
    low = max(0, round(value * (1 - percentage) / million) * million)
    high = max(low, round(value * (1 + percentage) / million) * million)
    return f"£{low / million:g}m–£{high / million:g}m"


def visible_player_data(player, level, free_agent=False):
    """Build display-only information; never change the underlying player."""
    row = {
        "Name": player["name"], "Position": player["position"], "Age": player["age"]
    }
    if free_agent:
        row.update({
            "Overall": player["overall"],
            "Potential": player["potential"] if level == FULLY_SCOUTED else "Unknown",
            "Value": "Unknown" if level < FULLY_SCOUTED else _exact_money(player["value"]),
            "Wage": _exact_money(player["wage"]),
        })
        return row
    if level == UNSCOUTED:
        row.update({"Overall": "?", "Potential": "?", "Value": "Unknown"})
    elif level == BASIC:
        row.update({
            "Overall": _number_range(player["overall"], 4, 0, 99),
            "Potential": "Unknown",
            "Value": _money_range(player["value"], .20),
        })
    elif level == SCOUTED:
        row.update({
            "Overall": _number_range(player["overall"], 2, 0, 99),
            "Potential": _number_range(player["potential"], 3, 0, 99),
            "Value": _money_range(player["value"], .08),
        })
    else:
        row.update({
            "Overall": player["overall"], "Potential": player["potential"],
            "Value": _exact_money(player["value"]),
            "Fitness": player.get("fitness", 100),
            "Morale": player.get("morale", 50), "Form": player.get("form", []),
            "Wage": _exact_money(player.get("wage", 0)),
            "Contract": player.get("contract_years", 0),
            "Status": _status(player),
        })
    return row


def _exact_money(value):
    return f"£{value:,.0f}"


def _status(player):
    if player.get("injured"):
        return "Injured"
    if player.get("suspended") or player.get("suspension_gameweeks", 0):
        return "Suspended"
    return "Available"


def assign_scout(player, club, user_club, knowledge, assignments, season, gameweek):
    """Start one assignment, subject to the simple three-slot rules."""
    identifier = player_id(player)
    if club == user_club or knowledge.get(identifier, UNSCOUTED) >= FULLY_SCOUTED:
        return False, "This player is already fully known."
    if len(assignments) >= MAX_ACTIVE_ASSIGNMENTS:
        return False, "All three scouting slots are currently in use."
    if any(item["player_id"] == identifier for item in assignments):
        return False, "That player is already being scouted."
    assignments.append({
        "player_id": identifier, "player_name": player["name"], "club": club,
        "season_assigned": season, "gameweek_assigned": gameweek,
    })
    return True, f"Scout assigned to {player['name']}."


def process_scouting(assignments, knowledge, reports, squads, season, gameweek,
                     processed_gameweeks, free_agents=()):
    """Finish eligible work once only after a later completed gameweek."""
    marker = (season, gameweek)
    if marker in processed_gameweeks:
        return []
    processed_gameweeks.add(marker)
    players = {
        player_id(player): (club, player)
        for club, squad in squads.items() for player in squad
    }
    players.update({player_id(player): ("Free Agent", player) for player in free_agents})
    completed = []
    for assignment in list(assignments):
        found = players.get(assignment["player_id"])
        created = (assignment["season_assigned"], assignment["gameweek_assigned"])
        if found is None:
            assignments.remove(assignment)  # Retired players free the slot.
        elif (season, gameweek) > created:
            club, player = found
            level = min(FULLY_SCOUTED, knowledge.get(player_id(player), 0) + 1)
            knowledge[player_id(player)] = level
            report = {
                "player_id": player_id(player), "player_name": player["name"],
                "club": club, "season": season, "gameweek_completed": gameweek,
                "knowledge_level": level,
            }
            reports.append(report)
            completed.append(report)
            assignments.remove(assignment)
    return completed


def remove_invalid_assignments(assignments, squads, free_agents=()):
    """Discard assignments whose player no longer exists (for example retirees)."""
    active_ids = {player_id(p) for squad in squads.values() for p in squad}
    active_ids.update(player_id(player) for player in free_agents)
    assignments[:] = [a for a in assignments if a["player_id"] in active_ids]
    return assignments
