"""Tests for player rotation, fitness and injury rules."""

from copy import deepcopy
import random
import unittest

from career import start_next_season
from data import CLUBS, SQUADS, calculate_team_strength
from fitness import (
    ensure_player_health,
    injury_chance,
    is_available,
    process_gameweek_health,
)
from retirement import generate_youth_player
from transfer import buy_player


class FitnessTests(unittest.TestCase):
    def setUp(self):
        self.squad = deepcopy(SQUADS["Arsenal"])
        self.starters = self.squad[:11]

    def test_initial_fitness_is_valid(self):
        self.assertTrue(all(0 <= player["fitness"] <= 100 for player in self.squad))

    def test_starters_tire_and_non_starters_recover_with_safe_bounds(self):
        for player in self.squad:
            player["fitness"] = 90
        self.squad[-1]["fitness"] = 99
        process_gameweek_health(self.squad, self.starters, 1, set(), random.Random(4))

        self.assertTrue(all(player["fitness"] < 90 for player in self.starters))
        self.assertEqual(self.squad[-1]["fitness"], 100)
        self.assertTrue(all(0 <= player["fitness"] <= 100 for player in self.squad))

    def test_fitness_cannot_fall_below_zero(self):
        for player in self.starters:
            player["fitness"] = 1
        process_gameweek_health(self.squad, self.starters, 1, set(), random.Random(2))
        self.assertTrue(all(player["fitness"] >= 0 for player in self.starters))

    def test_lower_fitness_reduces_strength(self):
        fit = deepcopy(self.starters)
        tired = deepcopy(self.starters)
        for player in tired:
            player["fitness"] = 60
        self.assertLess(calculate_team_strength(tired), calculate_team_strength(fit))

    def test_injured_player_is_not_available(self):
        player = self.squad[0]
        player.update({"injured": True, "injury_gameweeks": 2})
        self.assertFalse(is_available(player))

    def test_low_fitness_has_greater_injury_risk_on_average(self):
        fit = {"fitness": 100, "overall": 80}
        tired = {"fitness": 20, "overall": 80}
        ensure_player_health(fit)
        ensure_player_health(tired)
        rng = random.Random(12)
        fit_injuries = sum(rng.random() < injury_chance(fit) for _ in range(10000))
        tired_injuries = sum(rng.random() < injury_chance(tired) for _ in range(10000))
        self.assertGreater(tired_injuries, fit_injuries * 4)

    def test_injury_ticks_down_and_player_recovers_at_zero(self):
        player = self.squad[-1]
        player.update({"injured": True, "injury_gameweeks": 2})
        events = process_gameweek_health(self.squad, self.starters, 1, set(), random.Random(8))
        self.assertEqual(player["injury_gameweeks"], 1)
        events = process_gameweek_health(self.squad, self.starters, 2, set(), random.Random(8))
        self.assertFalse(player["injured"])
        self.assertIn(player["name"], events["recoveries"])

    def test_duplicate_gameweek_does_not_apply_fatigue_twice(self):
        processed = set()
        process_gameweek_health(self.squad, self.starters, 1, processed, random.Random(5))
        fitness = [player["fitness"] for player in self.squad]
        event = process_gameweek_health(self.squad, self.starters, 1, processed, random.Random(6))
        self.assertEqual(fitness, [player["fitness"] for player in self.squad])
        self.assertFalse(event["processed"])

    def test_bought_and_youth_players_have_valid_health(self):
        squads = deepcopy(SQUADS)
        name = squads["Chelsea"][0]["name"]
        self.assertTrue(buy_player(squads, "Arsenal", name, 500_000_000)[0])
        bought = next(player for player in squads["Arsenal"] if player["name"] == name)
        youth = generate_youth_player("ST", rng=random.Random(3))
        for player in (bought, youth):
            self.assertTrue(0 <= player["fitness"] <= 100)
            self.assertFalse(player["injured"])

    def test_new_season_restores_health(self):
        self.squad[0].update({"fitness": 12, "injured": True, "injury_gameweeks": 4})
        squads = deepcopy(SQUADS)
        squads["Arsenal"] = self.squad
        state = {
            "season_number": 1, "processed_seasons": {1}, "career_squads": squads,
            "active_club": "Arsenal", "player_statistics": {},
        }
        start_next_season(state, CLUBS, random.Random(1))
        self.assertTrue(all(player["fitness"] == 100 for player in self.squad))
        self.assertTrue(all(not player["injured"] for player in self.squad))


if __name__ == "__main__":
    unittest.main()
