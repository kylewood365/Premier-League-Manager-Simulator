"""Simple transfer operations, kept separate from the Streamlit interface."""


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


def buy_player(squads, user_club, player_name, budget):
    """Buy an available player and return the updated budget and message."""
    selling_club, player = find_player(squads, player_name)
    if player is None or selling_club == user_club:
        return False, budget, "That player is no longer available to buy."
    if budget < player["value"]:
        return False, budget, "You do not have enough transfer budget for this player."

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
