"""Career-specific simulator budget generation."""

from data import CLUB_BUDGETS, CLUB_WAGE_BUDGETS


def career_budget_mappings(squads):
    """Return positive budgets, with deterministic estimates for unknown clubs."""
    transfers, wages = {}, {}
    for club, squad in squads.items():
        if club in CLUB_BUDGETS:
            transfers[club] = CLUB_BUDGETS[club]
            wages[club] = CLUB_WAGE_BUDGETS[club]
            continue
        average = sum(p.get("overall", 65) for p in squad) / max(1, len(squad))
        # These are deliberately simulator estimates, not representations of real finances.
        transfers[club] = int(max(25_000_000, min(100_000_000, 30_000_000 + (average - 65) * 3_000_000)))
        wages[club] = int(max(900_000, min(2_500_000, 900_000 + transfers[club] // 70)))
    return transfers, wages
