"""Checks for the starter squad data."""

import unittest

from data import CLUBS, SQUADS


class SquadDataTests(unittest.TestCase):
    def test_every_club_has_exactly_eleven_players(self):
        self.assertEqual(set(CLUBS), set(SQUADS))
        for squad in SQUADS.values():
            self.assertEqual(len(squad), 11)

    def test_all_ratings_are_between_65_and_90(self):
        for squad in SQUADS.values():
            for player in squad:
                self.assertGreaterEqual(player["overall"], 65)
                self.assertLessEqual(player["overall"], 90)


if __name__ == "__main__":
    unittest.main()
