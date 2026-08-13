"""End-to-end test for the Streamlit match and league table flow."""

import unittest

from streamlit.testing.v1 import AppTest

from data import CLUBS, SQUADS


class StreamlitFlowTests(unittest.TestCase):
    def test_simulating_a_match_updates_and_displays_the_table(self):
        app = AppTest.from_file("app.py").run()
        app.selectbox[0].select("Arsenal")
        app.button[0].click().run()
        app.multiselect[0].set_value(
            [player["name"] for player in SQUADS["Arsenal"][:11]]
        ).run()
        app.selectbox[1].select("Chelsea")
        app.button[1].click().run()

        table = app.session_state["league_table"]
        self.assertEqual(len(table), len(CLUBS))
        self.assertEqual(table["Arsenal"]["Played"], 1)
        self.assertEqual(table["Chelsea"]["Played"], 1)
        self.assertEqual(sum(row["Played"] for row in table.values()), 2)
        self.assertIn("Full Time", [heading.value for heading in app.subheader])
        self.assertIn("League Table", [heading.value for heading in app.subheader])
        self.assertEqual(len(app.dataframe[-1].value), 20)


if __name__ == "__main__":
    unittest.main()
