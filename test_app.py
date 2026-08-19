"""End-to-end test for the Streamlit gameweek flow."""

import unittest

from streamlit.testing.v1 import AppTest

from app import matchday_player_label, players_for_ids
from data import CLUBS, SQUADS


class StreamlitFlowTests(unittest.TestCase):
    @staticmethod
    def click_button(app, label):
        button = next(item for item in app.button if item.label == label)
        return button.click().run(timeout=10)

    def test_playing_a_gameweek_updates_and_displays_all_results(self):
        app = AppTest.from_file("app.py").run()
        app.selectbox[0].select("Arsenal")
        app.button[0].click().run(timeout=10)
        self.assertIn("Arsenal Manager Dashboard", [heading.value for heading in app.header])
        app.sidebar.radio[0].set_value("Matchday").run(timeout=10)
        starters = SQUADS["Arsenal"][:11]
        app.session_state["starting_xi_Arsenal_1"] = [player["id"] for player in starters]
        app.run(timeout=10)
        app = self.click_button(app, "Kickoff")
        self.assertEqual(app.session_state["match_phase"], "Half-time")
        app = self.click_button(app, "Start Second Half")
        self.assertEqual(app.session_state["match_phase"], "Second half")
        app = self.click_button(app, "Full-time")

        table = app.session_state["league_table"]
        self.assertEqual(len(table), len(CLUBS))
        self.assertTrue(all(row["Played"] == 1 for row in table.values()))
        self.assertEqual(len(app.session_state["gameweek_results"]), 10)
        self.assertIn("Gameweek 1 Results", [heading.value for heading in app.subheader])
        self.assertIn("League Table", [heading.value for heading in app.subheader])
        self.assertEqual(len(app.dataframe[-1].value), 20)

        app.button[-1].click().run()
        self.assertEqual(app.session_state["current_gameweek"], 2)

    def test_database_selector_starts_offline_with_fictional_squads(self):
        app = AppTest.from_file("app.py").run()
        self.assertEqual(app.radio[0].label, "Career Database")
        app.radio[0].set_value("Fictional Squads").run()
        self.assertIn("Arsenal", app.selectbox[0].options)

    def test_matchday_selectors_show_positions_without_changing_names(self):
        app = AppTest.from_file("app.py").run()
        app.selectbox[0].select("Arsenal")
        app.button[0].click().run(timeout=10)
        app.sidebar.radio[0].set_value("Matchday").run(timeout=10)

        self.assertTrue(any(button.label.startswith("＋\nST") for button in app.button))
        app.session_state["starting_xi_Arsenal_1"] = [
            player["id"] for player in SQUADS["Arsenal"][:11]
        ]
        app.run(timeout=10)
        rendered_labels = [button.label for button in app.button]
        self.assertTrue(all(any(player["name"] in label for label in rendered_labels)
                            for player in SQUADS["Arsenal"][:11]))
        self.assertTrue(any(button.label == "＋\nSUB" for button in app.button))
        self.assertEqual(
            app.session_state["starting_xi_Arsenal_1"],
            [player["id"] for player in SQUADS["Arsenal"][:11]],
        )
        self.assertTrue(all("(" not in player["name"] for player in SQUADS["Arsenal"]))

    def test_stable_ids_distinguish_duplicate_player_names(self):
        players = [
            {"id": "one", "name": "Same Name", "position": "MID"},
            {"id": "two", "name": "Same Name", "position": "FWD"},
        ]
        self.assertEqual(players_for_ids(players, ["two"]), [players[1]])
        self.assertEqual(matchday_player_label(players[1]), "Same Name (FWD)")


if __name__ == "__main__":
    unittest.main()
