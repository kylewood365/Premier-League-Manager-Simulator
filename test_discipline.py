"""Tests for cards, dismissals and league suspensions."""

from copy import deepcopy
import unittest

from career import start_next_season
from data import CLUBS, SQUADS
from discipline import (
    apply_discipline_events, ensure_player_discipline, process_suspensions,
    red_card_strength, simulate_player_cards,
)
from fitness import is_available
from stats import create_player_statistics, record_match_statistics
from tactics import validate_bench, validate_starting_xi


class YellowRng:
    """Book on yellow checks but never on straight-red checks."""

    def __init__(self):
        self.calls = 0

    def random(self):
        self.calls += 1
        return 0.01 if self.calls % 2 else 0.5

    def randint(self, start, end):
        return start


class DisciplineTests(unittest.TestCase):
    def setUp(self):
        self.squad = deepcopy(SQUADS["Arsenal"])

    def test_participants_get_yellows_but_unused_substitutes_do_not(self):
        starter = self.squad[0]
        unused = self.squad[12]
        events = simulate_player_cards([starter], [starter], YellowRng())
        self.assertTrue(any(event["type"] == "yellow" for event in events))
        self.assertNotIn(unused["name"], [event["player"] for event in events])

    def test_two_yellows_create_second_yellow_red_and_one_match_ban(self):
        player = self.squad[0]
        events = simulate_player_cards([player], [player], YellowRng())
        reds = [event for event in events if event["type"] == "red"]
        self.assertEqual(reds[0]["reason"], "second yellow")
        apply_discipline_events(self.squad, events)
        self.assertEqual(player["suspension_matches"], 1)

    def test_straight_red_creates_three_match_ban(self):
        player = self.squad[0]
        apply_discipline_events(self.squad, [{
            "player": player["name"], "minute": 20, "type": "red",
            "reason": "straight red",
        }])
        self.assertEqual(player["suspension_matches"], 3)

    def test_five_yellows_trigger_one_ban_without_retriggering(self):
        player = self.squad[0]
        yellow = {"player": player["name"], "minute": 20, "type": "yellow"}
        apply_discipline_events(self.squad, [yellow] * 5)
        self.assertEqual(player["league_yellow_cards"], 0)
        self.assertEqual(player["suspension_matches"], 1)

    def test_suspended_players_cannot_start_or_be_on_bench(self):
        xi = self.squad[:11]
        xi[0]["suspension_matches"] = 1
        with self.assertRaisesRegex(ValueError, "Suspended"):
            validate_starting_xi(xi, "4-3-3")
        xi[0]["suspension_matches"] = 0
        substitute = self.squad[11]
        substitute["suspension_matches"] = 1
        with self.assertRaisesRegex(ValueError, "Suspended"):
            validate_bench([substitute], xi)

    def test_new_ban_is_not_immediately_served_then_eventually_expires(self):
        player = self.squad[0]
        ensure_player_discipline(player)
        player["suspension_matches"] = 2
        processed = set()
        process_suspensions(self.squad, 1, processed, {player["name"]})
        self.assertEqual(player["suspension_matches"], 2)
        process_suspensions(self.squad, 2, processed)
        self.assertEqual(player["suspension_matches"], 1)
        recovery = process_suspensions(self.squad, 3, processed)
        self.assertIn(player["name"], recovery["recoveries"])
        self.assertTrue(is_available(player))

    def test_duplicate_processing_and_card_statistics_are_idempotent(self):
        player = self.squad[0]
        player["suspension_matches"] = 2
        processed = set()
        process_suspensions(self.squad, 2, processed)
        process_suspensions(self.squad, 2, processed)
        self.assertEqual(player["suspension_matches"], 1)
        stats = create_player_statistics(self.squad)
        cards = [{"player": player["name"], "type": "yellow", "minute": 4}]
        recorded = set()
        record_match_statistics(stats, [player], [], 2, recorded, cards)
        record_match_statistics(stats, [player], [], 2, recorded, cards)
        self.assertEqual(stats[player["name"]]["yellow_cards"], 1)

    def test_red_card_reduces_strength_more_for_two_dismissals(self):
        self.assertLess(red_card_strength(80, 1), 80)
        self.assertLess(red_card_strength(80, 2), red_card_strength(80, 1))

    def test_new_season_clears_accumulation_bans_and_card_stats(self):
        player = self.squad[0]
        player.update(league_yellow_cards=4, suspension_matches=2)
        state = {
            "season_number": 1, "processed_seasons": {1}, "active_club": "Arsenal",
            "career_squads": {**deepcopy(SQUADS), "Arsenal": self.squad},
            "player_statistics": {player["name"]: {
                "appearances": 2, "goals": 0, "yellow_cards": 4, "red_cards": 1,
            }},
        }
        start_next_season(state, CLUBS)
        self.assertEqual(player["league_yellow_cards"], 0)
        self.assertEqual(player["suspension_matches"], 0)
        self.assertNotIn("yellow_cards", state["player_statistics"][player["name"]])


if __name__ == "__main__":
    unittest.main()
