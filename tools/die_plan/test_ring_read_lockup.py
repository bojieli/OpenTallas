"""SELLK-1 (S81-ALLFIX-SVC SERDES-RING 11-24): clock.ring_hold.read_lockup emits SELLK=1 on count-aligned rings; 0 added
cycles, lane cycles and strap K unchanged; absent / false = byte-same RTL; read_lockup_types scopes it.
Ring bench: rtl/test/meso/sellk/run.sh."""
import copy
import count_align_bind as CAB
from clock_landings import Landings, ring_read_lockup
from test_clock_landings import ca_vehicle, B_BODY
from test_count_straps import strap_vehicle


def _rh(p, **kw):
    p.setdefault("clock", {}).setdefault("ring_hold", {"sender_ps": 80}).update(kw)


def test_absent_or_false_is_byte_same():
    for veh in (ca_vehicle, strap_vehicle):
        p, t = veh()
        base = Landings(copy.deepcopy(p), copy.deepcopy(t)).type_rtl("B", B_BODY)
        _rh(p, read_lockup=False)
        assert Landings(copy.deepcopy(p), copy.deepcopy(t)).type_rtl("B", B_BODY) == base
        assert ".SELLK(" not in base


def test_read_lockup_adds_only_the_parameter_and_no_cycle():
    p, t = strap_vehicle()
    base = Landings(copy.deepcopy(p), copy.deepcopy(t))
    text0 = base.type_rtl("B", B_BODY)
    _rh(p, read_lockup=True)
    on = Landings(copy.deepcopy(p), copy.deepcopy(t))
    text = on.type_rtl("B", B_BODY)
    assert ".SELLK(1)" in text and text.replace(", .SELLK(1)", "") == text0
    rec = on.manifest()["reset_placements"]["B"]["y"]
    assert rec["read_lockup"] is True and rec["read_lockup_added_cycles"] == 0
    assert on.manifest()["lane_added_cycles"] == base.manifest()["lane_added_cycles"]
    assert CAB.strap_ties(t["count_aligned"], p) == CAB.strap_ties(t["count_aligned"], strap_vehicle()[0])


def test_read_lockup_types_scope():
    p, t = strap_vehicle()
    base = Landings(copy.deepcopy(p), copy.deepcopy(t)).type_rtl("B", B_BODY)
    _rh(p, read_lockup=True, read_lockup_types=["other"])
    assert Landings(copy.deepcopy(p), copy.deepcopy(t)).type_rtl("B", B_BODY) == base
    p["clock"]["ring_hold"]["read_lockup_types"] = ["B"]
    assert ".SELLK(1)" in Landings(copy.deepcopy(p), copy.deepcopy(t)).type_rtl("B", B_BODY)
    assert ring_read_lockup(p, "B__cl1234") and not ring_read_lockup(p, "C")
    assert ring_read_lockup(p) is True and ring_read_lockup({"clock": {"ring_hold": {"read_lockup": 1}}}) is False
