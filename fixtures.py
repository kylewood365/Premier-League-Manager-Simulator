"""Premier League fixture and gameweek helpers."""


def generate_fixtures(clubs):
    """Create a 38-gameweek double round-robin schedule for 20 clubs."""
    if len(clubs) != 20 or len(set(clubs)) != 20:
        raise ValueError("Fixtures require exactly 20 different clubs.")

    # The circle method fixes one club and rotates the other 19 each week.
    rotation = list(clubs)
    first_half = []
    for round_index in range(len(clubs) - 1):
        matches = []
        for match_index in range(len(clubs) // 2):
            first = rotation[match_index]
            second = rotation[-(match_index + 1)]

            # Alternating the first pairing avoids one club always being home.
            if match_index == 0 and round_index % 2:
                first, second = second, first
            elif match_index > 0 and round_index % 2 == 0:
                first, second = second, first
            matches.append({"home": first, "away": second})

        first_half.append(matches)
        rotation = [rotation[0], rotation[-1], *rotation[1:-1]]

    # Reverse every venue for the second half of the season.
    second_half = [
        [{"home": match["away"], "away": match["home"]} for match in matches]
        for matches in first_half
    ]
    return first_half + second_half


def get_club_fixture(fixtures, gameweek_number, club):
    """Return a club's fixture in a one-based gameweek."""
    if not 1 <= gameweek_number <= len(fixtures):
        return None
    for match in fixtures[gameweek_number - 1]:
        if club in (match["home"], match["away"]):
            return match
    return None


def advance_gameweek(current_gameweek, completed_gameweeks, total_gameweeks=38):
    """Move on only after the current gameweek has been completed."""
    if current_gameweek not in completed_gameweeks:
        raise ValueError("Complete the current gameweek before continuing.")
    if current_gameweek >= total_gameweeks:
        return None
    return current_gameweek + 1
