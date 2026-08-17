"""Tests for formations and tactical matchday management."""

from copy import deepcopy
import random
import unittest

from data import SQUADS
from fitness import process_gameweek_health
from game import simulate_match
from stats import create_player_statistics, record_match_statistics
from tactics import (
    FORMATIONS, TACTICAL_STYLES, apply_substitutions, tactical_strength,
    validate_bench, validate_starting_xi,
)


class TacticsTests(unittest.TestCase):
    def setUp(self):
        self.squad = deepcopy(SQUADS["Arsenal"])

    def xi_for(self, formation):
        # The generated squad contains the extra centre-back and striker needed
        # by the three/five-defender and two-striker shapes.
        if formation == "4-3-3":
            return self.squad[:11]
        if formation == "4-2-3-1":
            return self.squad[:11]
        if formation == "4-4-2":
            return self.squad[:8] + [self.squad[9], self.squad[10], self.squad[14]]
        if formation == "3-5-2":
            return [self.squad[i] for i in (0, 2, 3, 12, 1, 4, 5, 6, 7, 10, 14)]
        return [self.squad[i] for i in (0, 1, 2, 3, 4, 12, 5, 6, 7, 10, 14)]

    def test_every_formation_has_eleven_slots_and_accepts_a_valid_xi(self):
        for formation, slots in FORMATIONS.items():
            self.assertEqual(len(slots), 11)
            self.assertTrue(validate_starting_xi(self.xi_for(formation), formation))

    def test_invalid_shape_and_injured_starter_are_rejected(self):
        xi = self.squad[:11]
        xi[10]["position"] = "GK"
        with self.assertRaises(ValueError):
            validate_starting_xi(xi, "4-3-3")
        xi[10]["position"] = "ST"
        xi[0]["injured"] = True
        with self.assertRaises(ValueError):
            validate_starting_xi(xi, "4-3-3")

    def test_bench_rules(self):
        xi = self.squad[:11]
        with self.assertRaises(ValueError):
            validate_bench([xi[0]], xi)
        oversized = [dict(self.squad[11], name=f"Sub {i}") for i in range(8)]
        with self.assertRaises(ValueError):
            validate_bench(oversized, xi)
        injured = [dict(self.squad[11], injured=True)]
        with self.assertRaises(ValueError):
            validate_bench(injured, xi)

    def test_substitution_limits_and_same_substitute_cannot_enter_twice(self):
        xi, bench = self.squad[:11], self.squad[11:]
        with self.assertRaises(ValueError):
            apply_substitutions(xi, bench, [(xi[0]["name"], bench[0]["name"])] * 6)
        changes = [(xi[0]["name"], bench[0]["name"]), (xi[1]["name"], bench[0]["name"])]
        with self.assertRaises(ValueError):
            apply_substitutions(xi, bench, changes)

    def test_every_tactical_style_changes_or_preserves_strength_as_documented(self):
        results = {style: tactical_strength(80, style) for style in TACTICAL_STYLES}
        self.assertEqual(results["Balanced"], (80, 80))
        self.assertGreater(results["Attacking"][0], results["Balanced"][0])
        self.assertGreater(results["Defensive"][1], results["Balanced"][1])
        self.assertEqual(len(set(results.values())), len(TACTICAL_STYLES))

    def test_attacking_scores_more_and_defensive_concedes_less_on_average(self):
        totals = {"balanced_for": 0, "attacking_for": 0, "balanced_against": 0, "defensive_against": 0}
        for seed in range(1500):
            balanced = simulate_match("A", "B", 80, 80, random.Random(seed))
            attacking = simulate_match("A", "B", 80, 80, random.Random(seed), "Attacking")
            defensive = simulate_match("A", "B", 80, 80, random.Random(seed), "Defensive")
            totals["balanced_for"] += balanced["home_score"]
            totals["attacking_for"] += attacking["home_score"]
            totals["balanced_against"] += balanced["away_score"]
            totals["defensive_against"] += defensive["away_score"]
        self.assertGreater(totals["attacking_for"], totals["balanced_for"])
        self.assertLess(totals["defensive_against"], totals["balanced_against"])

    def test_substitute_appearance_unused_bench_and_lower_fatigue(self):
        starters, substitute, unused = self.squad[:11], self.squad[11], self.squad[12]
        statistics = create_player_statistics(self.squad)
        record_match_statistics(statistics, starters + [substitute], [], 1, set())
        self.assertEqual(statistics[substitute["name"]]["appearances"], 1)
        self.assertEqual(statistics[unused["name"]]["appearances"], 0)
        for player in self.squad:
            player["fitness"] = 80
        process_gameweek_health(self.squad, starters, 1, set(), random.Random(4), [substitute])
        self.assertGreater(substitute["fitness"], starters[0]["fitness"])
        self.assertGreater(unused["fitness"], substitute["fitness"])

    def test_half_scores_sum_to_final_score(self):
        match = simulate_match("A", "B", 82, 79, random.Random(9))
        self.assertEqual(match["home_score"], match["first_half_home_score"] + match["second_half_home_score"])
        self.assertEqual(match["away_score"], match["first_half_away_score"] + match["second_half_away_score"])


if __name__ == "__main__":
    unittest.main()
