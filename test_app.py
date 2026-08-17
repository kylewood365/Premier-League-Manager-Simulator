"""End-to-end test for the Streamlit gameweek flow."""

import unittest

from streamlit.testing.v1 import AppTest

from data import CLUBS, SQUADS


class StreamlitFlowTests(unittest.TestCase):
    @staticmethod
    def click_button(app, label):
        button = next(item for item in app.button if item.label == label)
        return button.click().run()

    def test_playing_a_gameweek_updates_and_displays_all_results(self):
        app = AppTest.from_file("app.py").run()
        app.selectbox[0].select("Arsenal")
        app.button[0].click().run()
        self.assertIn("Arsenal Manager Dashboard", [heading.value for heading in app.header])
        app.sidebar.radio[0].set_value("Matchday").run()
        app.multiselect[0].set_value(
            [player["name"] for player in SQUADS["Arsenal"][:11]]
        ).run()
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


if __name__ == "__main__":
    unittest.main()
