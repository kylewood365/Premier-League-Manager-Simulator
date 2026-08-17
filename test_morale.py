"""Tests for morale, recent form and their modest match effect."""

import random
import unittest

from fitness import effective_rating
from morale import (
    add_form_rating, calculate_match_rating, ensure_player_morale_form,
    form_score, process_match_morale_and_form, reset_morale_form_for_new_season,
)


def player(name="Player", morale=75, overall=75, age=25):
    return {
        "name": name, "position": "CM", "age": age, "overall": overall,
        "fitness": 100, "injured": False, "injury_gameweeks": 0,
        "morale": morale, "recent_form": [],
    }


class MoraleAndFormTests(unittest.TestCase):
    def process(self, result="win", goals=None, cards=None, squad=None, week=1):
        squad = squad or [player()]
        processed = set()
        process_match_morale_and_form(
            squad, squad[:1], [], [], result, goals or [], cards or [],
            week, processed, rng=random.Random(1),
        )
        return squad, processed

    def test_morale_is_clamped(self):
        high = player(morale=1000)
        low = player("Low", morale=-50)
        self.assertEqual(ensure_player_morale_form(high)["morale"], 100)
        self.assertEqual(ensure_player_morale_form(low)["morale"], 0)

    def test_result_and_goal_changes(self):
        winners, _ = self.process("win")
        losers, _ = self.process("loss")
        scorers, _ = self.process("draw", [{"player": "Player", "minute": 1}])
        self.assertGreater(winners[0]["morale"], 75)
        self.assertLess(losers[0]["morale"], 75)
        self.assertGreater(scorers[0]["morale"], 75)

    def test_repeated_healthy_senior_omission_reduces_morale(self):
        omitted = player()
        processed = set()
        for week in range(1, 4):
            process_match_morale_and_form(
                [omitted], [], [], [], "draw", [], [], week, processed,
                rng=random.Random(week),
            )
        self.assertLess(omitted["morale"], 75)

    def test_form_keeps_five_and_averages(self):
        member = player()
        for rating in (7.1, 8.4, 6.8, 7.9, 8.1, 9.0):
            add_form_rating(member, rating)
        self.assertEqual(member["recent_form"], [8.4, 6.8, 7.9, 8.1, 9.0])
        self.assertEqual(form_score(member), 8.0)
        self.assertIsNone(form_score(player()))

    def test_goals_raise_and_red_cards_lower_ratings(self):
        ordinary = calculate_match_rating()
        self.assertGreater(calculate_match_rating(goals=1), ordinary)
        self.assertLess(calculate_match_rating(red_card=True), ordinary)

    def test_soft_factors_are_small_beside_fitness_and_overall(self):
        neutral = player()
        high = player("High", morale=100)
        low = player("Low", morale=0)
        add_form_rating(high, 9)
        add_form_rating(low, 6)
        self.assertGreater(effective_rating(high), effective_rating(neutral))
        self.assertLess(effective_rating(low), effective_rating(neutral))
        self.assertLess(effective_rating(high) - effective_rating(low), 7)
        unfit = player("Unfit", morale=100)
        unfit["fitness"] = 50
        add_form_rating(unfit, 9)
        self.assertGreater(effective_rating(neutral) - effective_rating(unfit), 10)
        elite = player("Elite", overall=90, morale=0)
        add_form_rating(elite, 6)
        self.assertGreater(effective_rating(elite), effective_rating(high))

    def test_new_season_rebalances_morale_and_clears_form(self):
        member = player(morale=10)
        add_form_rating(member, 8)
        reset_morale_form_for_new_season([member])
        self.assertGreater(member["morale"], 10)
        self.assertEqual(member["recent_form"], [])

    def test_gameweek_cannot_be_processed_twice(self):
        member = player()
        processed = set()
        args = ([member], [member], [], [], "win", [], [], 1, processed)
        self.assertTrue(process_match_morale_and_form(*args, rng=random.Random(1)))
        state = (member["morale"], list(member["recent_form"]))
        self.assertFalse(process_match_morale_and_form(*args, rng=random.Random(1)))
        self.assertEqual(state, (member["morale"], member["recent_form"]))


if __name__ == "__main__":
    unittest.main()
