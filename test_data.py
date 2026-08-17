"""Checks for the starter squad data."""

import unittest

from data import (
    CLUBS,
    CLUB_BUDGETS,
    CLUB_WAGE_BUDGETS,
    SQUADS,
    calculate_team_strength,
    get_best_starting_xi,
)


class SquadDataTests(unittest.TestCase):
    def test_club_list_matches_the_2026_27_premier_league(self):
        self.assertEqual(len(CLUBS), 20)
        self.assertEqual(CLUBS, sorted(CLUBS))
        for club in ("Coventry City", "Hull City", "Ipswich Town"):
            self.assertIn(club, CLUBS)
        for club in ("Burnley", "West Ham United", "Wolverhampton Wanderers"):
            self.assertNotIn(club, CLUBS)

    def test_every_club_has_transfer_and_wage_budgets(self):
        self.assertEqual(set(CLUB_BUDGETS), set(CLUBS))
        self.assertEqual(set(CLUB_WAGE_BUDGETS), set(CLUBS))

    def test_every_club_has_enough_players_to_choose_an_xi(self):
        self.assertEqual(set(CLUBS), set(SQUADS))
        for squad in SQUADS.values():
            self.assertGreaterEqual(len(squad), 11)

    def test_all_ratings_are_between_65_and_90(self):
        for squad in SQUADS.values():
            for player in squad:
                self.assertGreaterEqual(player["overall"], 65)
                self.assertLessEqual(player["overall"], 90)

    def test_eleven_selected_players_produce_the_correct_average(self):
        starting_xi = [{"overall": rating} for rating in range(70, 81)]

        self.assertEqual(calculate_team_strength(starting_xi), 75.0)

    def test_team_strength_requires_exactly_eleven_players(self):
        with self.assertRaisesRegex(ValueError, "exactly 11"):
            calculate_team_strength(SQUADS["Arsenal"][:10])

    def test_best_starting_xi_contains_the_top_eleven_ratings(self):
        best_xi = get_best_starting_xi("Arsenal")

        self.assertEqual(len(best_xi), 11)
        self.assertEqual(
            [player["overall"] for player in best_xi],
            sorted(
                [player["overall"] for player in SQUADS["Arsenal"]], reverse=True
            )[:11],
        )


if __name__ == "__main__":
    unittest.main()
