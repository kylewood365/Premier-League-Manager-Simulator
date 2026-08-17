"""Player contract and weekly wage rules."""


MAX_CONTRACT_YEARS = 5


def calculate_weekly_wage(overall, age, potential=None):
    """Return a rounded, fictional Premier League-style weekly wage."""
    wage = max(5_000, (overall - 55) ** 2 * 175)
    if age <= 23 and (potential or overall) >= 82:
        wage *= 1.12
    return max(5_000, int(round(wage / 1_000)) * 1_000)


def starting_contract_years(age):
    """Give younger players longer initial deals, between one and five years."""
    if age <= 21:
        return 5
    if age <= 24:
        return 4
    if age <= 28:
        return 3
    if age <= 32:
        return 2
    return 1


def requested_weekly_wage(player):
    """Calculate the wage a player asks for when extending their deal."""
    ability_wage = calculate_weekly_wage(
        player["overall"], player["age"], player.get("potential")
    )
    increase = 1.12 if player["age"] <= 24 and player.get("potential", 0) > player["overall"] else 1.06
    return int(round(max(ability_wage, player["wage"] * increase) / 1_000)) * 1_000


def calculate_wage_spend(squad):
    """Return the club's total weekly wage commitment."""
    return sum(player["wage"] for player in squad)


def renew_contract(player, extension_years, squad, wage_budget):
    """Extend a deal when its length and new wage are affordable."""
    if extension_years not in (1, 2, 3, 4):
        return False, "Choose an extension between 1 and 4 years."
    if player["contract_years"] + extension_years > MAX_CONTRACT_YEARS:
        return False, "A contract cannot exceed 5 total years."
    new_wage = requested_weekly_wage(player)
    new_spend = calculate_wage_spend(squad) - player["wage"] + new_wage
    if new_spend > wage_budget:
        return False, "This renewal would exceed the weekly wage budget."
    player["wage"] = new_wage
    player["contract_years"] += extension_years
    return True, f"Contract renewed for {extension_years} year(s)."


def process_contracts(squads, free_agents, season, processed_seasons):
    """Count down contracts once and move expired players to free agency.

    A minimal academy promotion protects every club from falling below eleven
    players when several deals expire together. This is a safety net, not a
    substitute for the manager renewing contracts to preserve squad quality.
    """
    if season in processed_seasons:
        return None
    events = []
    for club, squad in squads.items():
        for player in list(squad):
            player["contract_years"] = max(0, player["contract_years"] - 1)
            if player["contract_years"] == 0:
                squad.remove(player)
                player["club"] = None
                free_agents.append(player)
                event = {"player": player["name"], "club": club, "type": "expired"}
                if len(squad) < 11:
                    # Local import avoids the module-level contracts/retirement
                    # dependency cycle.
                    from retirement import generate_youth_player
                    youth = generate_youth_player(
                        player["position"], (member["name"] for member in squad)
                    )
                    squad.append(youth)
                    event["youth"] = youth
                events.append(event)
            elif player["contract_years"] == 1:
                events.append({"player": player["name"], "club": club, "type": "warning"})
    processed_seasons.add(season)
    return events


def age_free_agents(free_agents):
    """Keep unattached players aging between seasons."""
    for player in free_agents:
        player["age"] += 1
