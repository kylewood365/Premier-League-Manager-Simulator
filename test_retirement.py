"""Tests for retirement and fictional youth regeneration."""

import random
import unittest

from retirement import (
    generate_youth_player,
    process_retirements,
    retirement_probability,
    should_retire,
)


class RetirementTests(unittest.TestCase):
    def test_under_35_never_retires_and_40_always_retires(self):
        self.assertFalse(should_retire({"age": 34}, random.Random(1)))
        self.assertTrue(should_retire({"age": 40}, random.Random(1)))

    def test_probability_increases_with_age(self):
        chances = [retirement_probability(age) for age in range(35, 41)]
        self.assertTrue(all(left < right for left, right in zip(chances, chances[1:])))

    def test_retiree_is_removed_and_replaced_by_valid_youth(self):
        retiree = {
            "name": "Old Player", "position": "CB", "age": 40,
            "overall": 60, "potential": 60, "value": 1,
        }
        squads = {"Example FC": [retiree]}
        history = []
        events = process_retirements(squads, 3, history, rng=random.Random(2))

        self.assertEqual(len(events), 1)
        self.assertNotIn(retiree, squads["Example FC"])
        self.assertEqual(len(squads["Example FC"]), 1)
        youth = squads["Example FC"][0]
        self.assertEqual(youth["position"], "CB")
        self.assertIn(youth["age"], range(16, 20))
        self.assertGreaterEqual(youth["potential"], youth["overall"])
        self.assertLessEqual(youth["potential"], 94)
        self.assertGreater(youth["value"], 0)
        self.assertEqual(history[0]["season"], 3)

    def test_every_retiree_gets_one_persistent_replacement(self):
        squads = {"Example FC": [
            {"name": f"Old {number}", "position": "CM", "age": 40,
             "overall": 60, "potential": 60, "value": 1}
            for number in range(2)
        ]}
        processed = set()
        history = []
        events = process_retirements(
            squads, 1, history, processed, random.Random(4)
        )
        youth_names = [player["name"] for player in squads["Example FC"]]

        self.assertEqual(len(events), 2)
        self.assertEqual(len(youth_names), 2)
        self.assertIsNone(process_retirements(
            squads, 1, history, processed, random.Random(5)
        ))
        self.assertEqual(youth_names, [p["name"] for p in squads["Example FC"]])
        self.assertEqual(len(history), 2)

    def test_generated_youth_constraints(self):
        for seed in range(100):
            youth = generate_youth_player("ST", rng=random.Random(seed))
            self.assertIn(youth["age"], range(16, 20))
            self.assertGreaterEqual(youth["potential"], youth["overall"])
            self.assertLessEqual(youth["potential"], 94)
            self.assertGreater(youth["value"], 0)


if __name__ == "__main__":
    unittest.main()
