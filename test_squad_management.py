"""Tests for squad roles, satisfaction, promises and requests."""

from copy import deepcopy

from data import SQUADS
from retirement import generate_youth_player
from squad_management import (
    ROLE_EXPECTATIONS, SQUAD_ROLES, accept_transfer_request, assign_default_roles,
    change_squad_role, ensure_squad_management, process_playing_time,
    promise_more_playing_time, reset_squad_management_for_new_season,
    satisfaction_label,
)
from transfer import buy_player


class AlwaysRequest:
    def random(self):
        return 0.0


def player(name="Player", role="Important Player", age=26, overall=80):
    return ensure_squad_management({
        "name": name, "position": "CM", "age": age, "overall": overall,
        "morale": 60,
    }, role=role)


def test_every_player_receives_a_predictable_valid_default_role():
    squad = deepcopy(SQUADS["Arsenal"])
    assign_default_roles(squad)
    assert all(member["squad_role"] in SQUAD_ROLES for member in squad)
    assert [p["squad_role"] for p in squad] == [
        p["squad_role"] for p in assign_default_roles(deepcopy(SQUADS["Arsenal"]))
    ]


def test_star_expectation_is_higher_than_prospect_expectation():
    assert ROLE_EXPECTATIONS["Star Player"] > ROLE_EXPECTATIONS["Prospect"]


def test_unavailable_game_does_not_count_or_reduce_satisfaction():
    member = player()
    member["injured"] = True
    process_playing_time([member], [], 1)
    assert member["available_league_games"] == 0
    assert member["role_satisfaction"] == 60


def test_repeated_omissions_hurt_important_player_more_than_prospect():
    important, prospect = player("A"), player("B", "Prospect", 19, 62)
    for week in range(1, 6):
        process_playing_time([important, prospect], [], week)
    assert important["role_satisfaction"] < 60
    assert prospect["role_satisfaction"] >= important["role_satisfaction"]
    assert important["morale"] > 50  # gradual, rather than an extreme drop


def test_one_omission_cannot_create_a_transfer_request():
    member = player()
    member["role_satisfaction"] = 20
    process_playing_time([member], [], 1, AlwaysRequest())
    assert member["transfer_requested"] is False


def test_sustained_very_unhappy_status_can_create_request():
    member = player()
    member["role_satisfaction"] = 20
    for week in range(1, 4):
        process_playing_time([member], [], week, AlwaysRequest())
    assert member["transfer_requested"] is True


def test_promise_fulfilment_and_failure_adjust_morale():
    fulfilled = player("Fulfilled")
    failed = player("Failed")
    promise_more_playing_time(fulfilled)
    promise_more_playing_time(failed)
    assert fulfilled["playing_time_promise"]["active"] is True
    starting = fulfilled["morale"]
    for week in range(1, 6):
        process_playing_time([fulfilled], [fulfilled], week)
        process_playing_time([failed], [], week)
    assert fulfilled["playing_time_promise"]["outcome"] == "fulfilled"
    assert fulfilled["morale"] > starting
    assert failed["playing_time_promise"]["outcome"] == "failed"
    assert failed["morale"] < starting


def test_accept_request_lists_player_and_role_change_keeps_unhappiness():
    member = player()
    member.update(transfer_requested=True, role_satisfaction=20)
    assert accept_transfer_request(member) is True
    assert member["transfer_listed"] is True
    change_squad_role(member, "Prospect")
    assert satisfaction_label(member["role_satisfaction"]) == "Very Unhappy"


def test_new_signing_has_clean_valid_management_state():
    squads = {"User": [player("Home")], "Other": [player("Signing")]}
    squads["Other"][0].update(value=1, wage=1, fitness=80, injured=False,
                               injury_gameweeks=0, transfer_requested=True)
    ok, _, _ = buy_player(squads, "User", "Signing", 10)
    assert ok and squads["User"][-1]["squad_role"] in SQUAD_ROLES
    assert squads["User"][-1]["transfer_requested"] is False


def test_youth_players_are_prospects():
    assert generate_youth_player("CM")["squad_role"] == "Prospect"


def test_duplicate_processing_does_not_repeat_progress():
    member = player()
    promise_more_playing_time(member)
    process_playing_time([member], [], 1)
    snapshot = (member["available_league_games"], member["role_satisfaction"],
                member["playing_time_promise"]["games_elapsed"])
    process_playing_time([member], [], 1)
    assert snapshot == (member["available_league_games"], member["role_satisfaction"],
                        member["playing_time_promise"]["games_elapsed"])


def test_new_season_only_resets_season_tracking_and_completed_promise():
    member = player()
    member.update(available_league_games=5, participated_league_games=2,
                  transfer_requested=True, transfer_listed=True)
    promise_more_playing_time(member)
    member["playing_time_promise"].update(active=False, outcome="failed")
    role, morale = member["squad_role"], member["morale"]
    reset_squad_management_for_new_season([member])
    assert (member["available_league_games"], member["participated_league_games"]) == (0, 0)
    assert member["squad_role"] == role and member["morale"] == morale
    assert member["transfer_requested"] and member["transfer_listed"]
    assert member["playing_time_promise"] is None
