"""Tests for the first match simulation feature."""

import random
import unittest

from game import simulate_match


class MatchSimulationTests(unittest.TestCase):
    def test_simulation_returns_non_negative_integer_scores(self):
        match = simulate_match("Arsenal", "Chelsea", 85, 82, random.Random(1))

        self.assertIsInstance(match["user_score"], int)
        self.assertIsInstance(match["opponent_score"], int)
        self.assertGreaterEqual(match["user_score"], 0)
        self.assertGreaterEqual(match["opponent_score"], 0)

    def test_simulation_returns_both_clubs(self):
        match = simulate_match("Liverpool", "Everton", 85, 74, random.Random(2))

        self.assertEqual(match["user_club"], "Liverpool")
        self.assertEqual(match["opponent"], "Everton")

    def test_stronger_team_has_a_higher_average_win_rate(self):
        simulations = 5000
        strong_wins = 0
        weak_wins = 0
        random_generator = random.Random(10)

        for _ in range(simulations):
            match = simulate_match(
                "Strong FC", "Weak FC", 88, 70, random_generator
            )
            strong_wins += match["winner"] == "Strong FC"
            weak_wins += match["winner"] == "Weak FC"

        self.assertGreater(strong_wins / simulations, weak_wins / simulations)


if __name__ == "__main__":
    unittest.main()
