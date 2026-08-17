"""Tests for score-aware team match statistics and season history."""

import random
import unittest

from match_stats import (calculate_season_aggregates, combine_half_statistics,
                         generate_half_statistics, record_match_history)


class MatchStatisticsTests(unittest.TestCase):
    def test_invariants_and_score_are_respected(self):
        for seed in range(100):
            stats = generate_half_statistics(82, 78, 3, 1, rng=random.Random(seed))
            self.assertEqual(stats["home"]["possession"] + stats["away"]["possession"], 100)
            for side, goals in (("home", 3), ("away", 1)):
                self.assertGreaterEqual(stats[side]["shots"], stats[side]["shots_on_target"])
                self.assertGreaterEqual(stats[side]["shots_on_target"], goals)
                self.assertGreaterEqual(stats[side]["xg"], 0)

    def _averages(self, home_strength=80, away_strength=80,
                  home_style="Balanced", away_style="Balanced", home_reds=0):
        rows = [generate_half_statistics(
            home_strength, away_strength, 0, 0, home_style, away_style,
            home_reds, 0, random.Random(seed)
        ) for seed in range(600)]
        return tuple(sum(row["home"][key] for row in rows) / len(rows)
                     for key in ("possession", "shots", "xg")) + (
            sum(row["away"]["shots"] for row in rows) / len(rows),
            sum(row["away"]["xg"] for row in rows) / len(rows),
        )

    def test_strength_and_tactics_have_expected_long_run_effects(self):
        balanced = self._averages()
        strong = self._averages(88, 72)
        possession = self._averages(home_style="Possession")
        attacking = self._averages(home_style="Attacking")
        defensive = self._averages(home_style="Defensive")
        counter = self._averages(home_style="Counter Attack")
        reds = self._averages(home_reds=1)
        self.assertGreater(strong[1], balanced[1])
        self.assertGreater(strong[2], balanced[2])
        self.assertGreater(possession[0], balanced[0])
        self.assertGreater(attacking[1], balanced[1])
        self.assertGreater(attacking[2], balanced[2])
        self.assertLess(defensive[3], balanced[3])
        self.assertLess(defensive[4], balanced[4])
        self.assertLess(counter[0], balanced[0])
        self.assertGreater(counter[2], 0.25)
        self.assertLess(reds[0], balanced[0])
        self.assertLess(reds[1], balanced[1])

    def test_halves_combine_without_mutating_them(self):
        first = generate_half_statistics(80, 78, 1, 0, rng=random.Random(2))
        second = generate_half_statistics(82, 78, 0, 2, "Attacking", rng=random.Random(3))
        total = combine_half_statistics(first, second)
        self.assertEqual(total["home"]["shots"], first["home"]["shots"] + second["home"]["shots"])
        self.assertEqual(total["away"]["shots_on_target"], first["away"]["shots_on_target"] + second["away"]["shots_on_target"])
        self.assertEqual(total["home"]["xg"], round(first["home"]["xg"] + second["home"]["xg"], 2))
        self.assertEqual(total["home"]["possession"] + total["away"]["possession"], 100)

    def test_history_is_fixed_unique_and_season_aggregates_are_filtered(self):
        history = []
        row = {"season": 1, "gameweek": 1, "possession": 55, "shots": 10,
               "shots_on_target": 4, "xg": 1.25, "goals": 2}
        self.assertTrue(record_match_history(history, row))
        changed = dict(row, shots=99)
        self.assertFalse(record_match_history(history, changed))
        record_match_history(history, dict(row, season=2, shots=8, xg=0.75, goals=1))
        totals = calculate_season_aggregates(history, 1)
        self.assertEqual(totals["matches"], 1)
        self.assertEqual(totals["total_shots"], 10)
        self.assertEqual(totals["total_goals"], 2)
        self.assertEqual(calculate_season_aggregates(history, 3)["total_xg"], 0)


if __name__ == "__main__":
    unittest.main()
