"""Simple transfer operations, kept separate from the Streamlit interface."""

from fitness import ensure_player_health
from morale import ensure_player_morale_form


def format_money(amount):
    """Display a whole-pound amount in a familiar football format."""
    return f"£{amount:,.0f}"


def find_player(squads, player_name):
    """Return the player's club and record, or two Nones if unavailable."""
    for club, squad in squads.items():
        for player in squad:
            if player["name"] == player_name:
                return club, player
    return None, None


def buy_player(squads, user_club, player_name, budget, wage_budget=None):
    """Buy an available player and return the updated budget and message."""
    selling_club, player = find_player(squads, player_name)
    if player is None or selling_club == user_club:
        return False, budget, "That player is no longer available to buy."
    if budget < player["value"]:
        return False, budget, "You do not have enough transfer budget for this player."
    if wage_budget is not None:
        from contracts import calculate_wage_spend
        if calculate_wage_spend(squads[user_club]) + player["wage"] > wage_budget:
            return False, budget, "This transfer would exceed your weekly wage budget."

    ensure_player_health(player)
    ensure_player_morale_form(player)
    # Detailed AI health is not simulated, so a player arriving from an AI club
    # is ready to join the manager's rotation.
    player.update({"fitness": 100, "injured": False, "injury_gameweeks": 0})
    squads[selling_club].remove(player)
    squads[user_club].append(player)
    return True, budget - player["value"], f"Signed {player_name}!"


def sell_player(squads, user_club, player_name, budget, transfer_pool):
    """Sell a player into a simple pool while preserving a valid squad."""
    if len(squads[user_club]) <= 11:
        return False, budget, "You must keep at least 11 players in your squad."

    player = next(
        (item for item in squads[user_club] if item["name"] == player_name), None
    )
    if player is None:
        return False, budget, "That player is no longer in your squad."

    squads[user_club].remove(player)
    transfer_pool.append(player)
    return True, budget + player["value"], f"Sold {player_name}!"


def sign_free_agent(squads, user_club, free_agents, player_name, contract_years, wage_budget):
    """Sign an unattached player without a transfer fee."""
    from contracts import calculate_wage_spend
    player = next((item for item in free_agents if item["name"] == player_name), None)
    if player is None:
        return False, "That free agent is no longer available."
    if contract_years not in range(1, 6):
        return False, "Choose a contract between 1 and 5 years."
    if calculate_wage_spend(squads[user_club]) + player["wage"] > wage_budget:
        return False, "This signing would exceed your weekly wage budget."
    # Free agents keep an existing health state where one was recorded.
    ensure_player_health(player)
    ensure_player_morale_form(player)
    free_agents.remove(player)
    player["contract_years"] = contract_years
    player.pop("club", None)
    squads[user_club].append(player)
    return True, f"Signed {player_name} on a free transfer!"
