"""Tests for preserving career state between Premier League seasons."""

from copy import deepcopy
import random
import unittest

from career import record_season_history, start_next_season
from data import CLUBS, SQUADS
from fixtures import generate_fixtures
from league import create_league_table
from progression import process_end_of_season
from stats import create_player_statistics
from transfer import buy_player


class CareerTransitionTests(unittest.TestCase):
    def test_completed_season_transitions_and_preserves_career_state(self):
        squads = deepcopy(SQUADS)
        bought_name = squads["Chelsea"][0]["name"]
        success, budget, _ = buy_player(squads, "Arsenal", bought_name, 500_000_000)
        self.assertTrue(success)

        statistics = create_player_statistics(squads["Arsenal"])
        for totals in statistics.values():
            totals.update({"appearances": 38, "goals": 2})
        table = create_league_table(CLUBS)
        table["Arsenal"]["Points"] = 90
        processed = set()
        summary = process_end_of_season(
            squads, "Arsenal", statistics, table, processed, 1, random.Random(7)
        )
        history = []
        self.assertTrue(record_season_history(history, 1, summary))

        ages = {player["name"]: player["age"] for player in squads["Arsenal"]}
        overalls = {player["name"]: player["overall"] for player in squads["Arsenal"]}
        old_fixtures = generate_fixtures(CLUBS)
        state = {
            "active_club": "Arsenal",
            "career_squads": squads,
            "transfer_budget": budget,
            "transfer_pool": [],
            "season_number": 1,
            "fixtures": old_fixtures,
            "league_table": table,
            "current_gameweek": 38,
            "completed_gameweeks": set(range(1, 39)),
            "recorded_stat_gameweeks": set(range(1, 39)),
            "player_statistics": statistics,
            "processed_seasons": processed,
            "career_history": history,
            "season_summary": summary,
        }

        start_next_season(state, CLUBS, random.Random(3))

        self.assertEqual(state["season_number"], 2)
        self.assertEqual(state["current_gameweek"], 1)
        self.assertEqual(len(state["fixtures"]), 38)
        self.assertIsNot(state["fixtures"], old_fixtures)
        self.assertTrue(all(len(gameweek) == 10 for gameweek in state["fixtures"]))
        self.assertTrue(
            all(
                value == 0
                for row in state["league_table"].values()
                for value in row.values()
            )
        )
        self.assertTrue(
            all(
                totals == {"appearances": 0, "goals": 0}
                for totals in state["player_statistics"].values()
            )
        )
        self.assertEqual(
            ages, {player["name"]: player["age"] for player in squads["Arsenal"]}
        )
        self.assertEqual(
            overalls,
            {player["name"]: player["overall"] for player in squads["Arsenal"]},
        )
        self.assertIn(bought_name, [player["name"] for player in squads["Arsenal"]])
        self.assertEqual(state["transfer_budget"], budget)
        self.assertEqual(history[0]["champion"], "Arsenal")
        self.assertNotIn("season_summary", state)

    def test_history_and_progression_are_idempotent_per_season(self):
        squads = deepcopy(SQUADS)
        stats = create_player_statistics(squads["Arsenal"])
        table = create_league_table(CLUBS)
        processed = set()
        summary = process_end_of_season(
            squads, "Arsenal", stats, table, processed, 1, random.Random(1)
        )
        ages_after = [player["age"] for squad in squads.values() for player in squad]

        self.assertIsNone(
            process_end_of_season(
                squads, "Arsenal", stats, table, processed, 1, random.Random(1)
            )
        )
        self.assertEqual(
            ages_after, [player["age"] for squad in squads.values() for player in squad]
        )
        history = []
        self.assertTrue(record_season_history(history, 1, summary))
        self.assertFalse(record_season_history(history, 1, summary))
        self.assertEqual(len(history), 1)


if __name__ == "__main__":
    unittest.main()
