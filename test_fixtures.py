"""Tests for the season fixture and gameweek flow."""

import random
import unittest
from collections import Counter

from data import CLUBS, SQUADS
from fixtures import advance_gameweek, generate_fixtures
from game import simulate_gameweek
from league import create_league_table


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.fixtures = generate_fixtures(CLUBS)

    def test_season_has_38_gameweeks_of_10_matches(self):
        self.assertEqual(len(self.fixtures), 38)
        self.assertTrue(all(len(gameweek) == 10 for gameweek in self.fixtures))

    def test_every_club_plays_once_each_gameweek_and_38_times(self):
        season_appearances = Counter()
        for gameweek in self.fixtures:
            clubs = [club for match in gameweek for club in match.values()]
            self.assertEqual(Counter(clubs), Counter({club: 1 for club in CLUBS}))
            season_appearances.update(clubs)
        self.assertEqual(season_appearances, Counter({club: 38 for club in CLUBS}))

    def test_every_pair_plays_twice_once_at_each_ground(self):
        meetings = Counter()
        venues = Counter()
        for gameweek in self.fixtures:
            for match in gameweek:
                pair = frozenset((match["home"], match["away"]))
                meetings[pair] += 1
                venues[(pair, match["home"])] += 1
        self.assertEqual(len(meetings), 190)
        self.assertTrue(all(count == 2 for count in meetings.values()))
        self.assertTrue(all(count == 1 for count in venues.values()))

    def test_gameweek_updates_every_club_and_cannot_be_counted_twice(self):
        table = create_league_table(CLUBS)
        completed = set()
        simulate_gameweek(
            1, self.fixtures, "Arsenal", SQUADS["Arsenal"][:11], table,
            completed, random.Random(1)
        )
        self.assertTrue(all(row["Played"] == 1 for row in table.values()))
        with self.assertRaisesRegex(ValueError, "already"):
            simulate_gameweek(
                1, self.fixtures, "Arsenal", SQUADS["Arsenal"][:11], table,
                completed, random.Random(1)
            )
        self.assertTrue(all(row["Played"] == 1 for row in table.values()))

    def test_career_advances_after_completion(self):
        self.assertEqual(advance_gameweek(1, {1}), 2)
        with self.assertRaisesRegex(ValueError, "Complete"):
            advance_gameweek(2, {1})
        self.assertIsNone(advance_gameweek(38, {38}))


if __name__ == "__main__":
    unittest.main()
