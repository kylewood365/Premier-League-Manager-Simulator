"""Tests for league table creation, updates, and sorting."""

import unittest

from league import create_league_table, get_sorted_league_table, update_league_table


class LeagueTableTests(unittest.TestCase):
    def setUp(self):
        self.table = create_league_table(["Alpha", "Bravo", "Charlie"])

    def test_every_club_starts_with_zero_statistics(self):
        self.assertEqual(len(self.table), 3)
        for row in self.table.values():
            self.assertTrue(all(value == 0 for value in row.values()))

    def test_win_awards_three_points_and_loss_awards_zero(self):
        update_league_table(self.table, "Alpha", "Bravo", 2, 0)

        self.assertEqual(self.table["Alpha"]["Won"], 1)
        self.assertEqual(self.table["Alpha"]["Points"], 3)
        self.assertEqual(self.table["Bravo"]["Lost"], 1)
        self.assertEqual(self.table["Bravo"]["Points"], 0)

    def test_draw_awards_one_point_to_each_club(self):
        update_league_table(self.table, "Alpha", "Bravo", 1, 1)

        self.assertEqual(self.table["Alpha"]["Drawn"], 1)
        self.assertEqual(self.table["Bravo"]["Drawn"], 1)
        self.assertEqual(self.table["Alpha"]["Points"], 1)
        self.assertEqual(self.table["Bravo"]["Points"], 1)

    def test_goals_and_goal_difference_update_for_both_clubs(self):
        update_league_table(self.table, "Alpha", "Bravo", 3, 1)

        self.assertEqual(self.table["Alpha"]["Goals For"], 3)
        self.assertEqual(self.table["Alpha"]["Goals Against"], 1)
        self.assertEqual(self.table["Alpha"]["Goal Difference"], 2)
        self.assertEqual(self.table["Bravo"]["Goals For"], 1)
        self.assertEqual(self.table["Bravo"]["Goals Against"], 3)
        self.assertEqual(self.table["Bravo"]["Goal Difference"], -2)

    def test_table_sorts_by_points_goal_difference_and_goals_for(self):
        # All three clubs finish on three points. Goal difference separates
        # Charlie, then goals scored separates Bravo from Alpha.
        update_league_table(self.table, "Alpha", "Bravo", 1, 0)
        update_league_table(self.table, "Bravo", "Charlie", 3, 1)
        update_league_table(self.table, "Charlie", "Alpha", 4, 0)

        sorted_clubs = [row["Club"] for row in get_sorted_league_table(self.table)]

        self.assertEqual(sorted_clubs, ["Charlie", "Bravo", "Alpha"])


if __name__ == "__main__":
    unittest.main()
