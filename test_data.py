"""Checks for the starter squad data."""

import unittest

from data import CLUBS, SQUADS, calculate_team_strength


class SquadDataTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
