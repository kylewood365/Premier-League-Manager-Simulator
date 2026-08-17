"""Tests for contracts, wages, expiry, and free transfers."""

from copy import deepcopy
import random
import unittest

from contracts import calculate_wage_spend, process_contracts, renew_contract
from data import CLUB_WAGE_BUDGETS, SQUADS
from retirement import generate_youth_player, process_retirements
from transfer import buy_player, sell_player, sign_free_agent


class ContractTests(unittest.TestCase):
    def test_starting_players_have_wages_and_valid_contracts(self):
        for squad in SQUADS.values():
            for player in squad:
                self.assertGreater(player["wage"], 0)
                self.assertIn(player["contract_years"], range(1, 6))

    def test_contracts_count_down_once_and_expiries_become_free_agents(self):
        player = deepcopy(SQUADS["Arsenal"][0])
        player["contract_years"] = 1
        squads, free_agents, processed = {"Arsenal": [player]}, [], set()
        events = process_contracts(squads, free_agents, 1, processed)
        self.assertEqual(player["contract_years"], 0)
        self.assertEqual(events[0]["type"], "expired")
        self.assertNotIn(player, squads["Arsenal"])
        self.assertIn(player, free_agents)
        self.assertIsNone(process_contracts(squads, free_agents, 1, processed))
        self.assertEqual(len(free_agents), 1)

    def test_renewal_updates_wage_and_length_but_never_exceeds_five(self):
        squad = deepcopy(SQUADS["Arsenal"])
        player = squad[0]
        player["contract_years"] = 1
        old_wage = player["wage"]
        success, _ = renew_contract(player, 4, squad, 10_000_000)
        self.assertTrue(success)
        self.assertEqual(player["contract_years"], 5)
        self.assertGreater(player["wage"], old_wage)
        self.assertFalse(renew_contract(player, 1, squad, 10_000_000)[0])

    def test_wage_spend_and_unaffordable_renewal(self):
        squad = deepcopy(SQUADS["Arsenal"])
        self.assertEqual(calculate_wage_spend(squad), sum(p["wage"] for p in squad))
        player = squad[0]
        before = (player["wage"], player["contract_years"])
        self.assertFalse(renew_contract(player, 1, squad, 0)[0])
        self.assertEqual((player["wage"], player["contract_years"]), before)

    def test_transfer_wages_are_checked_and_sale_reduces_spend(self):
        squads = deepcopy(SQUADS)
        target = squads["Chelsea"][0]
        self.assertFalse(buy_player(squads, "Arsenal", target["name"], 999_000_000, 0)[0])
        before = calculate_wage_spend(squads["Arsenal"])
        sold = squads["Arsenal"][0]
        self.assertTrue(sell_player(squads, "Arsenal", sold["name"], 0, [])[0])
        self.assertEqual(calculate_wage_spend(squads["Arsenal"]), before - sold["wage"])

    def test_free_agent_can_only_be_signed_once_when_affordable(self):
        squads = deepcopy(SQUADS)
        player = deepcopy(SQUADS["Chelsea"][0])
        free_agents = [player]
        budget = calculate_wage_spend(squads["Arsenal"]) + player["wage"]
        self.assertTrue(sign_free_agent(squads, "Arsenal", free_agents, player["name"], 3, budget)[0])
        self.assertFalse(sign_free_agent(squads, "Arsenal", free_agents, player["name"], 3, budget)[0])

    def test_youth_has_contract_and_retiree_never_becomes_free_agent(self):
        youth = generate_youth_player("ST", rng=random.Random(3))
        self.assertGreater(youth["wage"], 0)
        self.assertIn(youth["contract_years"], range(2, 6))
        retiree = {**deepcopy(SQUADS["Arsenal"][0]), "age": 40, "contract_years": 1}
        squads, free_agents = {"Arsenal": [retiree]}, []
        process_retirements(squads, 1, [], rng=random.Random(1))
        process_contracts(squads, free_agents, 1, set())
        self.assertNotIn(retiree, free_agents)


if __name__ == "__main__":
    unittest.main()
