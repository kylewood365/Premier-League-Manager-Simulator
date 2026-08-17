"""Formation, bench and substitution rules used on matchday."""

FORMATIONS = {
    "4-3-3": ("GK", "DEF", "DEF", "DEF", "DEF", "MID", "MID", "MID", "FWD", "FWD", "FWD"),
    "4-2-3-1": ("GK", "DEF", "DEF", "DEF", "DEF", "MID", "MID", "AM", "AM", "AM", "ST"),
    "4-4-2": ("GK", "DEF", "DEF", "DEF", "DEF", "MID", "MID", "MID", "MID", "FWD", "FWD"),
    "3-5-2": ("GK", "CB", "CB", "CB", "MID", "MID", "MID", "MID", "MID", "FWD", "FWD"),
    "5-3-2": ("GK", "DEF", "DEF", "DEF", "DEF", "DEF", "MID", "MID", "MID", "FWD", "FWD"),
}

TACTICAL_STYLES = ("Balanced", "Attacking", "Defensive", "Possession", "Counter Attack")

# Small attack/defence adjustments: ability remains by far the main input.
STYLE_MODIFIERS = {
    "Balanced": (0.0, 0.0),
    "Attacking": (2.0, -1.0),
    "Defensive": (-1.0, 2.0),
    "Possession": (0.8, 0.8),
    "Counter Attack": (1.2, -0.3),
}

# Match-stat effects are kept here so every simulation uses the same tactical
# identity.  Values are deliberately modest: the effective player strength is
# still the most important input.
STAT_STYLE_MODIFIERS = {
    "Balanced": {"possession": 0, "shots": 0.0, "quality": 0.0, "opponent": 0.0},
    "Attacking": {"possession": 1, "shots": 1.8, "quality": 0.02, "opponent": 0.7},
    "Defensive": {"possession": -2, "shots": -1.0, "quality": -0.01, "opponent": -1.2},
    "Possession": {"possession": 8, "shots": 0.4, "quality": 0.0, "opponent": -0.3},
    "Counter Attack": {"possession": -7, "shots": -0.5, "quality": 0.045, "opponent": 0.2},
}


def statistical_style(style):
    """Return the match-stat modifiers for a supported tactical style."""
    if style not in STAT_STYLE_MODIFIERS:
        raise ValueError("Unknown tactical style.")
    return STAT_STYLE_MODIFIERS[style]

POSITION_GROUPS = {
    "GK": {"GK"},
    "CB": {"CB"},
    "DEF": {"RB", "LB", "CB"},
    "MID": {"CM", "CAM", "LW", "RW", "LB", "RB"},
    "AM": {"CAM", "LW", "RW", "CM"},
    "ST": {"ST"},
    "FWD": {"ST", "LW", "RW", "CAM"},
}


def validate_starting_xi(players, formation):
    """Validate 11 healthy, unique players can fill every formation slot."""
    if formation not in FORMATIONS:
        raise ValueError("Unknown formation.")
    if len(players) != 11 or len({player["name"] for player in players}) != 11:
        raise ValueError("A starting XI must contain 11 different players.")
    if any(player.get("injured", False) for player in players):
        raise ValueError("Injured players cannot be selected in the starting XI.")
    if any(player.get("suspension_matches", 0) > 0 for player in players):
        raise ValueError("Suspended players cannot be selected in the starting XI.")

    # Backtracking avoids rejecting versatile combinations based on slot order.
    def fills(slot_index, remaining):
        if slot_index == len(FORMATIONS[formation]):
            return True
        allowed = POSITION_GROUPS[FORMATIONS[formation][slot_index]]
        return any(
            player["position"] in allowed
            and fills(slot_index + 1, remaining[:index] + remaining[index + 1 :])
            for index, player in enumerate(remaining)
        )

    if not fills(0, list(players)):
        raise ValueError(f"The selected players do not fit a {formation} formation.")
    return True


def validate_bench(bench, starting_xi):
    """Validate a healthy bench of no more than seven non-starters."""
    if len(bench) > 7:
        raise ValueError("The bench can contain at most 7 players.")
    names = [player["name"] for player in bench]
    if len(names) != len(set(names)):
        raise ValueError("A player cannot be named on the bench twice.")
    if set(names) & {player["name"] for player in starting_xi}:
        raise ValueError("Bench players cannot also be in the starting XI.")
    if any(player.get("injured", False) for player in bench):
        raise ValueError("Injured players cannot be selected on the bench.")
    if any(player.get("suspension_matches", 0) > 0 for player in bench):
        raise ValueError("Suspended players cannot be selected on the bench.")
    return True


def apply_substitutions(starting_xi, bench, substitutions):
    """Apply up to five ordered (player off, player on) changes."""
    validate_bench(bench, starting_xi)
    if len(substitutions) > 5:
        raise ValueError("No more than 5 substitutions are allowed.")
    pitch = list(starting_xi)
    bench_names = {player["name"]: player for player in bench}
    used = set()
    for change in substitutions:
        off_name, on_name = change
        pitch_names = {player["name"] for player in pitch}
        if off_name not in pitch_names:
            raise ValueError("The player coming off must currently be on the pitch.")
        if on_name not in bench_names:
            raise ValueError("The player coming on must be on the bench.")
        if on_name in used:
            raise ValueError("The same substitute cannot enter twice.")
        incoming = bench_names[on_name]
        if incoming.get("injured", False):
            raise ValueError("An injured player cannot be brought on.")
        pitch = [incoming if player["name"] == off_name else player for player in pitch]
        used.add(on_name)
    return pitch


def tactical_strength(team_strength, style):
    """Return attack and defence ratings after a deliberately small modifier."""
    if style not in STYLE_MODIFIERS:
        raise ValueError("Unknown tactical style.")
    attack, defence = STYLE_MODIFIERS[style]
    return team_strength + attack, team_strength + defence
