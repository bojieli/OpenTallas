"""WEN-LOCAL-1 (HEAD-W-SETUP 11-24): landing_wen_local emits WEN_LOCAL=1 on soft WREG count-aligned strap rings, 0 cycles, same K;
absent / false = byte-same RTL.  Proofs: rtl/test/meso/wen_local/{eq.sh,run.sh}."""
import copy
import pytest
import count_align_bind as CAB
from clock_landings import Landings, LandingError
from test_clock_landings import vehicle, B_BODY
from test_count_straps import strap_vehicle


def _wreg(p):
    p["partition_types"]["B"].setdefault("clock", {})["landing_ring_wreg"] = {"buses": ["y"], "dsrep": 1}
    return p


def test_wen_local_is_explicit_and_adds_no_cycle():
    p, t = strap_vehicle(); _wreg(p)
    base = Landings(copy.deepcopy(p), copy.deepcopy(t))
    baseline = base.type_rtl("B", B_BODY)
    assert ".WREG(1)" in baseline and "WEN_LOCAL" not in baseline
    p["partition_types"]["B"]["landing_wen_local"] = False
    assert Landings(copy.deepcopy(p), copy.deepcopy(t)).type_rtl("B", B_BODY) == baseline
    ties = CAB.strap_ties(t["count_aligned"], p)
    p["partition_types"]["B"]["landing_wen_local"] = True
    on = Landings(copy.deepcopy(p), copy.deepcopy(t))
    text = on.type_rtl("B", B_BODY)
    assert text.replace(", .WEN_LOCAL(1)", "") == baseline and ".WEN_LOCAL(1)" in text
    assert on.manifest()["reset_placements"]["B"]["y"]["ring_wen_local_added_cycles"] == 0
    assert on.manifest()["lane_added_cycles"] == base.manifest()["lane_added_cycles"]
    assert CAB.strap_ties(t["count_aligned"], p) == ties


def test_wen_local_rejects_plain_ring_or_non_boolean():
    p, t = vehicle()
    p["partition_types"]["B"]["landing_wen_local"] = True
    with pytest.raises(LandingError, match="count-aligned"):
        Landings(p, t).type_rtl("B", B_BODY)
    p, t = strap_vehicle()
    p["partition_types"]["B"]["landing_wen_local"] = "true"
    with pytest.raises(LandingError, match="boolean"):
        Landings(p, t).type_rtl("B", B_BODY)


def test_no_wreg_ring_keeps_its_parameters():
    p, t = strap_vehicle()
    base = Landings(copy.deepcopy(p), copy.deepcopy(t)).type_rtl("B", B_BODY)
    p["partition_types"]["B"]["landing_wen_local"] = True
    text = Landings(p, t).type_rtl("B", B_BODY)
    assert ("WEN_LOCAL" in text) == ("WREG(1)" in base)
