from data import SQUADS
from squad_builder import formation_slots, is_position_match, reconcile_assignments


def test_every_supported_formation_has_eleven_visual_slots():
    for formation in ("4-3-3", "4-2-3-1", "4-4-2", "3-5-2", "5-3-2"):
        slots = [slot for row in formation_slots(formation) for slot in row]
        assert len(slots) == 11
        assert len({slot["key"] for slot in slots}) == 11


def test_reconcile_preserves_unique_ids_and_prefers_compatible_slots():
    players = SQUADS["Arsenal"]
    goalkeeper = next(player for player in players if player["position"] == "GK")
    striker = next(player for player in players if player["position"] == "ST")
    result = reconcile_assignments({}, [goalkeeper["id"], striker["id"]], players, "4-3-3")
    assert len(result) == 2
    assert len(set(result.values())) == 2
    slots = {slot["key"]: slot for row in formation_slots("4-3-3") for slot in row}
    assert all(is_position_match(next(p for p in players if p["id"] == identifier), slots[key])
               for key, identifier in result.items())
