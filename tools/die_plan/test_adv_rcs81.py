"""FP-CONVERGE-S81: adv_rcs81 (STATUS-UP-REACH, CORE-LEG-OVERMACRO, RELAY-COHORT-SPAN): clean plan + a mutant each; MONLEG not skippable."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_rcs81 as R  # noqa: E402


def _t():
    return {"outline_um": [1000, 1000],
            "hard_cores": [{"inst": "u_a", "origin_um": [400, 400], "outline_um": [100, 100], "orient": "R0"}],
            "clock": {"landing_contract": {"collector_tree": {"root": [100, 100], "relays": [
                {"xy": [100 + i, 100], "tap": 1} for i in range(20)]},
                "pins": [{"name": "cland_up_ready", "xy_um": [200, 200]}, {"name": "cland_up_fault", "xy_um": [210, 200]}]}},
            "internal_stations": [{"conn": "bus:x", "launch": "core:u_p", "capture": "u_q", "from_um": [100, 100],
                                   "regs_um": [[300, 100]], "to_um": [600, 100]}]}


def test_status_up_clean_and_mutant():
    t = _t()
    assert R.status_up_reach(t) == []
    m = copy.deepcopy(t)
    m["clock"]["landing_contract"]["pins"][0]["xy_um"] = [900, 900]
    assert R.status_up_reach(m)[0][0] == "cland_up_ready"
    m["clock"]["landing_contract"]["collector_egress_um"] = [[500, 500], [900, 900]]
    assert R.status_up_reach(m) == []                       # an egress chain exempts the type


def test_core_leg_overmacro(monkeypatch):
    t = _t()
    monkeypatch.setattr(R.G, "hard_rects", lambda tt: [(400, 400, 500, 500, "u_a")])
    assert R.core_leg_overmacro(t) == []                   # the leg runs at y=100, clear of the core
    m = copy.deepcopy(t)
    m["internal_stations"][0].update(from_um=[100, 450], regs_um=[[300, 450]], to_um=[600, 450])   # the y=450 wire runs through the core
    r = R.core_leg_overmacro(m)
    assert r and r[0][1] >= 100 and r[0][2] == "u_a"       # 100 um of wire over the core


def test_relay_cohort_span():
    t = _t()
    assert R.relay_cohort_span(t) == []
    m = copy.deepcopy(t)
    m["clock"]["landing_contract"]["collector_tree"]["relays"][0]["xy"] = [100, 500]
    r = R.relay_cohort_span(m)
    assert r and r[0][0] == 1 and r[0][2] > R.SPAN_UM


def test_checks_registered():
    import plan_advisory as PA
    names = [n for n, _ in PA.CHECKS]
    for k in ("STATUS-UP-REACH", "CORE-LEG-OVERMACRO", "RELAY-COHORT-SPAN"):
        assert k in names
        assert k in R.findings_by_check


def test_relay_without_tap_is_not_a_cohort():
    m = _t()
    for r in m["clock"]["landing_contract"]["collector_tree"]["relays"]:
        r["tap"] = None
        r["xy"] = [r["xy"][0], r["xy"][1] + 900]
    m["clock"]["landing_contract"]["collector_tree"]["relays"][0]["xy"] = [900, 900]
    assert R.relay_cohort_span(m) == []
