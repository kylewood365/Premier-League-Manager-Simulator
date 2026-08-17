"""Tests for player goal events and season statistics."""

import random
import unittest

from data import SQUADS
from stats import (
    assign_goalscorers,
    create_player_statistics,
    ensure_player_statistics,
    get_current_squad_statistics,
    record_match_statistics,
)


class PlayerStatisticsTests(unittest.TestCase):
    def setUp(self):
        self.squad = SQUADS["Arsenal"][:11]
        self.statistics = create_player_statistics(SQUADS["Arsenal"])

    def test_goal_events_match_goal_total_and_have_valid_sorted_minutes(self):
        events = assign_goalscorers(self.squad, 5, random.Random(4))

        self.assertEqual(len(events), 5)
        self.assertTrue(all(1 <= event["minute"] <= 90 for event in events))
        self.assertEqual(
            [event["minute"] for event in events],
            sorted(event["minute"] for event in events),
        )

    def test_forwards_score_more_often_than_goalkeepers(self):
        events = assign_goalscorers(self.squad, 10_000, random.Random(8))
        positions = {
            player["name"]: player["position"] for player in self.squad
        }
        forward_goals = sum(
            positions[event["player"]] in {"ST", "LW", "RW"} for event in events
        )
        goalkeeper_goals = sum(
            positions[event["player"]] == "GK" for event in events
        )

        self.assertGreater(forward_goals, goalkeeper_goals)

    def test_starters_gain_appearances_and_scorers_gain_goals_once(self):
        scorer = self.squad[-1]["name"]
        events = [
            {"player": scorer, "minute": 12},
            {"player": scorer, "minute": 73},
        ]
        recorded = set()

        self.assertTrue(
            record_match_statistics(
                self.statistics, self.squad, events, 1, recorded
            )
        )
        self.assertTrue(
            all(
                self.statistics[player["name"]]["appearances"] == 1
                for player in self.squad
            )
        )
        self.assertEqual(self.statistics[scorer]["goals"], 2)

        self.assertFalse(
            record_match_statistics(
                self.statistics, self.squad, events, 1, recorded
            )
        )
        self.assertEqual(self.statistics[scorer], {"appearances": 1, "goals": 2})

    def test_bought_players_receive_statistics(self):
        new_player = SQUADS["Chelsea"][0]
        current_squad = SQUADS["Arsenal"] + [new_player]

        ensure_player_statistics(self.statistics, current_squad)

        self.assertEqual(
            self.statistics[new_player["name"]], {"appearances": 0, "goals": 0}
        )

    def test_sold_players_are_not_in_current_squad_rows(self):
        sold_player = SQUADS["Arsenal"][0]
        current_squad = SQUADS["Arsenal"][1:]

        rows = get_current_squad_statistics(current_squad, self.statistics)

        self.assertNotIn(sold_player["name"], [row["Player"] for row in rows])


if __name__ == "__main__":
    unittest.main()
