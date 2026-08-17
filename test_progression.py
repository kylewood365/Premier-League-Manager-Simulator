"""Tests for potential and end-of-season progression."""

from copy import deepcopy
import random
import unittest

from data import CLUBS, SQUADS
from league import create_league_table
from progression import calculate_overall_change, develop_player, get_league_champion, process_end_of_season
from stats import create_player_statistics


class ProgressionTests(unittest.TestCase):
    def test_all_players_have_valid_potential(self):
        for squad in SQUADS.values():
            for player in squad:
                self.assertGreaterEqual(player["potential"], player["overall"])
                self.assertLessEqual(player["potential"], 94)

    def test_player_cannot_develop_past_potential(self):
        player = {"age": 19, "overall": 79, "potential": 80, "position": "ST"}
        develop_player(player, {"appearances": 38, "goals": 30}, random.Random(1))
        self.assertEqual(player["overall"], 80)

    def test_high_performing_young_player_develops_more_than_old_player(self):
        young = {"age": 19, "overall": 70, "potential": 90, "position": "ST"}
        old = {"age": 29, "overall": 70, "potential": 90, "position": "ST"}
        young_total = sum(calculate_overall_change(young, {"appearances": 38, "goals": 20}, random.Random(i)) for i in range(100))
        old_total = sum(calculate_overall_change(old, {"appearances": 5, "goals": 0}, random.Random(i)) for i in range(100))
        self.assertGreater(young_total, old_total)

    def test_old_players_can_decline_without_falling_below_50(self):
        player = {"age": 38, "overall": 50, "potential": 80, "position": "CB"}
        change = develop_player(player, {"appearances": 30, "goals": 0}, random.Random(1))
        self.assertEqual(change, 0)
        self.assertEqual(player["overall"], 50)

    def test_season_processing_ages_revalues_and_only_runs_once(self):
        squads = deepcopy(SQUADS)
        stats = create_player_statistics(squads["Arsenal"])
        for value in stats.values():
            value["appearances"] = 38
        table = create_league_table(CLUBS)
        table["Arsenal"]["Points"] = 90
        processed = set()
        old_age = squads["Arsenal"][0]["age"]
        old_values = [player["value"] for player in squads["Arsenal"]]

        result = process_end_of_season(squads, "Arsenal", stats, table, processed, rng=random.Random(2))
        ages_after = [player["age"] for squad in squads.values() for player in squad]
        self.assertEqual(squads["Arsenal"][0]["age"], old_age + 1)
        self.assertTrue(any(player["value"] != old for player, old in zip(squads["Arsenal"], old_values)))
        self.assertIsNone(process_end_of_season(squads, "Arsenal", stats, table, processed, rng=random.Random(2)))
        self.assertEqual(ages_after, [player["age"] for squad in squads.values() for player in squad])
        self.assertEqual(result["champion"], "Arsenal")

    def test_champion_uses_table_tiebreakers(self):
        table = create_league_table(["Alpha", "Beta"])
        table["Alpha"].update({"Points": 80, "Goal Difference": 20, "Goals For": 60})
        table["Beta"].update({"Points": 80, "Goal Difference": 21, "Goals For": 50})
        self.assertEqual(get_league_champion(table), "Beta")


if __name__ == "__main__":
    unittest.main()
