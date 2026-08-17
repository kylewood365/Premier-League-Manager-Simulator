"""Tests for player values and the first transfer system."""

from copy import deepcopy
import unittest

from data import SQUADS, calculate_player_value
from transfer import buy_player, sell_player


class PlayerValueTests(unittest.TestCase):
    def test_every_player_has_a_positive_value(self):
        for squad in SQUADS.values():
            for player in squad:
                self.assertGreater(player["value"], 0)

    def test_higher_rated_players_are_worth_more_at_the_same_age(self):
        self.assertGreater(
            calculate_player_value(85, 24), calculate_player_value(75, 24)
        )

    def test_younger_players_are_worth_more_at_the_same_rating(self):
        self.assertGreater(
            calculate_player_value(80, 21), calculate_player_value(80, 29)
        )


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.squads = deepcopy(SQUADS)
        self.user_club = "Arsenal"
        self.selling_club = "Chelsea"
        self.player = self.squads[self.selling_club][0]
        self.budget = 200_000_000

    def test_buying_reduces_budget_and_moves_player_between_squads(self):
        success, budget, _ = buy_player(
            self.squads, self.user_club, self.player["name"], self.budget
        )

        self.assertTrue(success)
        self.assertEqual(budget, self.budget - self.player["value"])
        self.assertIn(self.player, self.squads[self.user_club])
        self.assertNotIn(self.player, self.squads[self.selling_club])
        self.assertEqual(self.player["club"], self.user_club)

    def test_unaffordable_purchase_is_rejected_without_moving_player(self):
        success, budget, _ = buy_player(
            self.squads, self.user_club, self.player["name"], 0
        )

        self.assertFalse(success)
        self.assertEqual(budget, 0)
        self.assertIn(self.player, self.squads[self.selling_club])
        self.assertNotIn(self.player, self.squads[self.user_club])

    def test_same_player_cannot_be_bought_twice(self):
        first, budget, _ = buy_player(
            self.squads, self.user_club, self.player["name"], self.budget
        )
        second, second_budget, _ = buy_player(
            self.squads, self.user_club, self.player["name"], budget
        )

        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(second_budget, budget)
        self.assertEqual(
            sum(p["name"] == self.player["name"] for p in self.squads[self.user_club]),
            1,
        )

    def test_selling_increases_budget_and_removes_player(self):
        player = self.squads[self.user_club][0]
        pool = []
        success, budget, _ = sell_player(
            self.squads, self.user_club, player["name"], self.budget, pool
        )

        self.assertTrue(success)
        self.assertEqual(budget, self.budget + player["value"])
        self.assertNotIn(player, self.squads[self.user_club])
        self.assertIn(player, pool)
        self.assertIsNone(player["club"])

    def test_transfers_change_players_available_for_starting_xi(self):
        original_name = self.squads[self.user_club][0]["name"]
        buy_player(self.squads, self.user_club, self.player["name"], self.budget)
        sell_player(self.squads, self.user_club, original_name, self.budget, [])
        available_names = [player["name"] for player in self.squads[self.user_club]]

        self.assertIn(self.player["name"], available_names)
        self.assertNotIn(original_name, available_names)

    def test_selling_cannot_leave_fewer_than_eleven_players(self):
        self.squads[self.user_club] = self.squads[self.user_club][:11]
        player = self.squads[self.user_club][0]

        success, budget, _ = sell_player(
            self.squads, self.user_club, player["name"], self.budget, []
        )

        self.assertFalse(success)
        self.assertEqual(budget, self.budget)
        self.assertIn(player, self.squads[self.user_club])


if __name__ == "__main__":
    unittest.main()
