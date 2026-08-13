"""Football data used by the Premier League Manager Simulator."""


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

# A balanced starting shape: one goalkeeper, four defenders, three midfielders,
# and three forwards.
STARTER_POSITIONS = ["GK", "RB", "CB", "CB", "LB", "CM", "CM", "CAM", "RW", "LW", "ST"]
STARTER_AGES = [27, 24, 28, 22, 25, 26, 21, 24, 23, 22, 27]
FIRST_NAMES = ["Alex", "Jamie", "Morgan", "Taylor", "Casey", "Jordan", "Riley", "Avery", "Cameron", "Rowan", "Finley"]

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


def create_squad(surname, base_rating, rating_changes):
    """Build one easy-to-read fictional squad."""
    squad = []
    for index in range(11):
        squad.append(
            {
                "name": f"{FIRST_NAMES[index]} {surname}",
                "position": STARTER_POSITIONS[index],
                "age": STARTER_AGES[index],
                "overall": base_rating + rating_changes[index],
            }
        )

    for index in range(len(SUBSTITUTE_FIRST_NAMES)):
        squad.append(
            {
                "name": f"{SUBSTITUTE_FIRST_NAMES[index]} {surname}",
                "position": SUBSTITUTE_POSITIONS[index],
                "age": SUBSTITUTE_AGES[index],
                "overall": base_rating + SUBSTITUTE_RATING_CHANGES[index],
            }
        )
    return squad


# SQUADS maps every selectable club to its full squad.
SQUADS = {
    club: create_squad(surname, base_rating, rating_changes)
    for club, (surname, base_rating, rating_changes) in CLUB_DETAILS.items()
}


def calculate_team_strength(starting_xi):
    """Return the average overall rating for a valid starting XI."""
    if len(starting_xi) != 11:
        raise ValueError("A starting XI must contain exactly 11 players.")

    total_rating = sum(player["overall"] for player in starting_xi)
    return round(total_rating / 11, 1)


def get_best_starting_xi(club):
    """Return a club's 11 highest-rated players."""
    return sorted(SQUADS[club], key=lambda player: player["overall"], reverse=True)[:11]
