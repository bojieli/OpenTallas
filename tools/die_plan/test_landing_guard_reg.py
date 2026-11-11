"""GUARD-REG-1 (CLAND-RING-NEGEDGE, COORD 11-11 09:47): landing_guard_reg / clock.landing_ring_guard_reg emit GUARD_REG=1
with the STATUS_REG=1 it needs on count-aligned rings; 0 added data/guard cycles, lane cycles and strap K unchanged;
absent / false = byte-same RTL.  Ring bench: rtl/test/meso/guard_reg/run.sh."""
import copy
import pytest
import count_align_bind as CAB
from clock_landings import Landings, LandingError
from test_clock_landings import ca_vehicle, vehicle, B_BODY
from test_count_straps import strap_vehicle


@pytest.mark.parametrize("strapped", [False, True])
def test_guard_reg_is_explicit_and_adds_no_cycle(strapped):
    p, t = strap_vehicle() if strapped else ca_vehicle()
    base = Landings(copy.deepcopy(p), copy.deepcopy(t))
    baseline = base.type_rtl("B", B_BODY)
    p["partition_types"]["B"]["landing_guard_reg"] = False
    assert Landings(copy.deepcopy(p), copy.deepcopy(t)).type_rtl("B", B_BODY) == baseline
    p["partition_types"]["B"]["landing_guard_reg"] = True
    on = Landings(copy.deepcopy(p), copy.deepcopy(t))
    text = on.type_rtl("B", B_BODY)
    assert ".STATUS_REG(1), .GUARD_REG(1)" in text
    assert text.replace(", .STATUS_REG(1), .GUARD_REG(1)", "") == baseline
    rec = on.manifest()["reset_placements"]["B"]["y"]
    assert rec["guard_reg"] is True and rec["guard_reg_added_cycles"] == 0
    assert rec["status_reg_added_data_cycles"] == 0 and rec["status_reg_added_fault_cycles"] == 1
    assert on.manifest()["lane_added_cycles"] == base.manifest()["lane_added_cycles"]
    # with landing_status_reg already on, guard_reg adds exactly the one parameter
    p2 = copy.deepcopy(p)
    p2["partition_types"]["B"]["landing_status_reg"] = True
    assert Landings(p2, copy.deepcopy(t)).type_rtl("B", B_BODY) == text
    if strapped:
        assert CAB.strap_ties(t["count_aligned"], p) == CAB.strap_ties(t["count_aligned"], strap_vehicle()[0])


def test_guard_reg_die_wide():
    p, t = strap_vehicle()
    base = Landings(copy.deepcopy(p), copy.deepcopy(t)).type_rtl("B", B_BODY)
    p.setdefault("clock", {})["landing_ring_guard_reg"] = True
    rtl = Landings(copy.deepcopy(p), copy.deepcopy(t)).type_rtl("B", B_BODY)
    assert rtl.replace(", .STATUS_REG(1), .GUARD_REG(1)", "") == base and ".GUARD_REG(1)" in rtl
    p["clock"]["landing_ring_guard_reg"] = 1
    with pytest.raises(ValueError):
        Landings(p, t).type_rtl("B", B_BODY)


def test_guard_reg_rejects_plain_ring_or_non_boolean():
    p, t = vehicle()
    p["partition_types"]["B"]["landing_guard_reg"] = True
    with pytest.raises(LandingError, match="count-aligned"):
        Landings(p, t).type_rtl("B", B_BODY)
    p, t = ca_vehicle()
    p["partition_types"]["B"]["landing_guard_reg"] = "true"
    with pytest.raises(LandingError, match="boolean"):
        Landings(p, t).type_rtl("B", B_BODY)
