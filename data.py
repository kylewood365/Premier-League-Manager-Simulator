"""Football data used by the Premier League Manager Simulator."""

from contracts import calculate_weekly_wage, starting_contract_years
from fitness import effective_rating
from morale import ensure_player_morale_form

# Keeping the club list here gives the UI and squad data one shared source.
CLUBS = [
    "Arsenal",
    "Aston Villa",
    "Bournemouth",
    "Brentford",
    "Brighton",
    "Burnley",
    "Chelsea",
    "Crystal Palace",
    "Everton",
    "Fulham",
    "Leeds United",
    "Liverpool",
    "Manchester City",
    "Manchester United",
    "Newcastle United",
    "Nottingham Forest",
    "Sunderland",
    "Tottenham Hotspur",
    "West Ham United",
    "Wolverhampton Wanderers",
]

# Transfer budgets are stored as whole pounds so calculations never need floats.
# The title challengers start with more spending power than smaller clubs.
CLUB_BUDGETS = {
    "Arsenal": 120_000_000,
    "Aston Villa": 75_000_000,
    "Bournemouth": 35_000_000,
    "Brentford": 40_000_000,
    "Brighton": 60_000_000,
    "Burnley": 30_000_000,
    "Chelsea": 140_000_000,
    "Crystal Palace": 50_000_000,
    "Everton": 40_000_000,
    "Fulham": 45_000_000,
    "Leeds United": 40_000_000,
    "Liverpool": 125_000_000,
    "Manchester City": 150_000_000,
    "Manchester United": 130_000_000,
    "Newcastle United": 110_000_000,
    "Nottingham Forest": 45_000_000,
    "Sunderland": 30_000_000,
    "Tottenham Hotspur": 100_000_000,
    "West Ham United": 60_000_000,
    "Wolverhampton Wanderers": 40_000_000,
}

# Weekly budgets scale with each club's financial strength.
CLUB_WAGE_BUDGETS = {
    club: 900_000 + transfer_budget // 70
    for club, transfer_budget in CLUB_BUDGETS.items()
}

# A balanced starting shape: one goalkeeper, four defenders, three midfielders,
# and three forwards.
STARTER_POSITIONS = ["GK", "RB", "CB", "CB", "LB", "CM", "CM", "CAM", "RW", "LW", "ST"]
STARTER_AGES = [27, 24, 28, 22, 25, 26, 21, 24, 23, 22, 27]
FIRST_NAMES = [
    "Alex",
    "Jamie",
    "Morgan",
    "Taylor",
    "Casey",
    "Jordan",
    "Riley",
    "Avery",
    "Cameron",
    "Rowan",
    "Finley",
]

# These extra players give the manager some alternatives when choosing an XI.
SUBSTITUTE_FIRST_NAMES = ["Charlie", "Sam", "Robin", "Drew"]
SUBSTITUTE_POSITIONS = ["GK", "CB", "CM", "ST"]
SUBSTITUTE_AGES = [23, 26, 20, 24]
SUBSTITUTE_RATING_CHANGES = [-3, -2, -2, -1]

# The surname, overall starting point, and small rating changes make every
# fictional squad distinct while keeping stronger clubs stronger overall.
CLUB_DETAILS = {
    "Arsenal": ("Ashford", 84, [2, 1, 1, 0, 1, 2, -1, 1, 2, 1, 3]),
    "Aston Villa": ("Vale", 78, [1, 0, 1, -1, 0, 2, -1, 1, 2, 0, 2]),
    "Bournemouth": ("Brook", 72, [1, 0, 0, -2, -1, 1, -2, 0, 1, -1, 2]),
    "Brentford": ("Beckett", 74, [1, 0, 1, -1, 0, 1, -2, 0, 2, -1, 2]),
    "Brighton": ("Bright", 75, [1, 1, 0, -1, 0, 2, -2, 1, 2, 0, 1]),
    "Burnley": ("Burns", 70, [1, 0, 1, -1, 0, 1, -2, 0, 1, -1, 2]),
    "Chelsea": ("Kingsley", 81, [2, 1, 0, -1, 1, 2, -1, 2, 2, 1, 2]),
    "Crystal Palace": ("Crystal", 75, [1, 0, 1, -1, 0, 1, -2, 1, 2, 0, 2]),
    "Everton": ("Everly", 73, [1, 0, 1, -1, 0, 1, -2, 0, 1, -1, 2]),
    "Fulham": ("Fulton", 74, [1, 0, 1, -1, 0, 2, -2, 1, 1, 0, 2]),
    "Leeds United": ("Leighton", 72, [1, 0, 1, -1, 0, 1, -2, 1, 2, -1, 2]),
    "Liverpool": ("Rivers", 84, [2, 1, 1, 0, 1, 2, -1, 2, 3, 2, 3]),
    "Manchester City": ("Mercer", 86, [2, 1, 1, 0, 1, 3, 0, 3, 2, 2, 4]),
    "Manchester United": ("Manning", 80, [2, 0, 1, -1, 0, 2, -2, 2, 2, 1, 3]),
    "Newcastle United": ("Newcombe", 79, [1, 1, 1, 0, 0, 2, -1, 1, 2, 1, 3]),
    "Nottingham Forest": ("Forrest", 73, [1, 0, 1, -1, 0, 1, -2, 0, 2, -1, 2]),
    "Sunderland": ("Sutton", 69, [1, 0, 1, -1, 0, 1, -2, 0, 2, -1, 2]),
    "Tottenham Hotspur": ("Hartley", 81, [2, 1, 1, -1, 1, 2, -1, 2, 2, 1, 3]),
    "West Ham United": ("Weston", 76, [1, 0, 1, -1, 0, 2, -2, 1, 2, 0, 2]),
    "Wolverhampton Wanderers": ("Wolfe", 73, [1, 0, 1, -1, 0, 1, -2, 1, 2, -1, 2]),
}


def calculate_player_value(overall, age):
    """Return a predictable value based on ability and remaining peak years."""
    ability_value = max(overall - 60, 1) * 2_000_000
    age_adjustment = max(0, 27 - age) * 1_000_000
    return ability_value + age_adjustment


def calculate_potential(overall, age):
    """Give younger players realistic room to grow, capped at 94."""
    growth_room = 7 if age <= 21 else 5 if age <= 24 else 3 if age <= 27 else 1
    return min(94, overall + growth_room)


def create_squad(surname, base_rating, rating_changes, club="club"):
    """Build one easy-to-read fictional squad."""
    squad = []
    for index in range(11):
        overall = base_rating + rating_changes[index]
        potential = calculate_potential(overall, STARTER_AGES[index])
        squad.append(
            ensure_player_morale_form({
                "id": f"{club.lower().replace(' ', '-')}-{index + 1}",
                "name": f"{FIRST_NAMES[index]} {surname}",
                "position": STARTER_POSITIONS[index],
                "age": STARTER_AGES[index],
                "overall": overall,
                "potential": potential,
                "value": calculate_player_value(
                    base_rating + rating_changes[index], STARTER_AGES[index]
                ),
                "wage": calculate_weekly_wage(overall, STARTER_AGES[index], potential),
                "contract_years": starting_contract_years(STARTER_AGES[index]),
                "fitness": 100,
                "injured": False,
                "injury_gameweeks": 0,
            })
        )

    for index in range(len(SUBSTITUTE_FIRST_NAMES)):
        overall = base_rating + SUBSTITUTE_RATING_CHANGES[index]
        potential = calculate_potential(overall, SUBSTITUTE_AGES[index])
        squad.append(
            ensure_player_morale_form({
                "id": f"{club.lower().replace(' ', '-')}-{index + 12}",
                "name": f"{SUBSTITUTE_FIRST_NAMES[index]} {surname}",
                "position": SUBSTITUTE_POSITIONS[index],
                "age": SUBSTITUTE_AGES[index],
                "overall": overall,
                "potential": potential,
                "value": calculate_player_value(
                    base_rating + SUBSTITUTE_RATING_CHANGES[index],
                    SUBSTITUTE_AGES[index],
                ),
                "wage": calculate_weekly_wage(overall, SUBSTITUTE_AGES[index], potential),
                "contract_years": starting_contract_years(SUBSTITUTE_AGES[index]),
                "fitness": 100,
                "injured": False,
                "injury_gameweeks": 0,
            })
        )
    return squad


# SQUADS maps every selectable club to its full squad.
SQUADS = {
    club: create_squad(surname, base_rating, rating_changes, club)
    for club, (surname, base_rating, rating_changes) in CLUB_DETAILS.items()
}


def calculate_team_strength(starting_xi):
    """Return the average overall rating for a valid starting XI."""
    if len(starting_xi) != 11:
        raise ValueError("A starting XI must contain exactly 11 players.")

    total_rating = sum(effective_rating(player) for player in starting_xi)
    return round(total_rating / 11, 1)


def get_best_starting_xi(club):
    """Return a club's 11 highest-rated players."""
    return sorted(SQUADS[club], key=lambda player: player["overall"], reverse=True)[:11]
