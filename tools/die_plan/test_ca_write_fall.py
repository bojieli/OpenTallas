"""DIE-HEAD-52 (COORD 10-31 18:0x (4), HEAD-RINGHOLD-2 17:49 (2)): die_sta_related --ca-write-fall prices a falling-edge
count-aligned ring writer (clock.ring_hold.write_edge fall, WFALL=1) the way count_align_bind.verify() does: the word is
written T/2 earlier (fstart sampled on the fclk fall), so the write->read lag is L + T/2.  Absent = byte-identical rows."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import count_align_bind as CAB  # noqa: E402
import die_sta_related as R  # noqa: E402


@pytest.fixture(autouse=True)
def _minmax_arrivals(monkeypatch):
    monkeypatch.setattr(R, "NOMINAL_ARRIVAL_DEFAULT", "minmax")


T = 833.0
REG = dict(clkq_max_wire_ps=48.0, clkq_min_nowire_ps=30.0, setup_ps=10.0, hold_ps=10.0)
L = [("a0", "b0", "A->B")]


def _taps():
    return {"a0": dict(part="A", cppr_node="A", late_ps=300.0, early_ps=280.0),
            "b0": dict(part="B", cppr_node="B", late_ps=520.0, early_ps=500.0)}


def _bind(depth=4, k=1):
    return {"sync_aperture_ps": 26.5, "ports": {
        "x": dict(src="A", dst="B", K=k, depth=depth, sched_lat=2, tree=False, L_lo_ps=k * T + 200.0,
                  L_hi_ps=k * T + 240.0, d_lo_ps=200.0, d_hi_ps=240.0, wander_ps=0.0)}, "regions": {}}


def test_absent_or_empty_is_unchanged():
    r0 = R.count_align_landed(L, _taps(), _bind(), T, REG)
    assert R.count_align_landed(L, _taps(), _bind(), T, REG, write_fall=set()) == r0
    assert R.count_align_landed(L, _taps(), _bind(), T, REG, write_fall={"other"}) == r0
    assert "write_fall_ports" not in r0 and "write_edge" not in r0["rows"][0]


def test_fall_writer_shifts_lag_by_half_period():
    x0 = R.count_align_landed(L, _taps(), _bind(), T, REG)["rows"][0]
    r1 = R.count_align_landed(L, _taps(), _bind(), T, REG, write_fall={"x"})
    x1 = r1["rows"][0]
    assert round(x1["L_lo_ps"] - x0["L_lo_ps"], 3) == T / 2 and round(x1["L_hi_ps"] - x0["L_hi_ps"], 3) == T / 2
    assert round(x1["margin_lo_ps"] - x0["margin_lo_ps"], 3) == T / 2
    assert round(x0["margin_hi_ps"] - x1["margin_hi_ps"], 3) == T / 2
    assert round(x1["slot_read_ps"] - x0["slot_read_ps"], 3) == T / 2
    assert x1["write_edge"] == "fall" and r1["write_fall_ports"] == 1


def test_same_shift_as_count_align_bind_verify():
    # verify(): L = (K + n_d - n_s) T + d + T/2 for fall ports -> low margin +T/2, high margin -T/2 (one model)
    x0 = R.count_align_landed(L, _taps(), _bind(depth=2, k=0), T, REG)["rows"][0]
    x1 = R.count_align_landed(L, _taps(), _bind(depth=2, k=0), T, REG, write_fall={"x"})["rows"][0]
    # K 0, depth 2: rising writer lo margin 200 - T/2 < 0 fails; the T/2-earlier fall write passes it
    assert x0["margin_lo_ps"] < 0 and not x0["lag_ok"]
    assert x1["margin_lo_ps"] == round(x0["margin_lo_ps"] + T / 2, 1) and x1["margin_hi_ps"] > 100 and x1["lag_ok"]


def test_high_side_mutant_is_caught():
    # depth 2, K 1: rising writer passes (hi margin 1.5T - (T + 240) = 176.5); the fall writer must FAIL hi
    x0 = R.count_align_landed(L, _taps(), _bind(depth=2), T, REG)["rows"][0]
    x1 = R.count_align_landed(L, _taps(), _bind(depth=2), T, REG, write_fall={"x"})["rows"][0]
    assert x0["lag_ok"] and not x1["lag_ok"] and x1["margin_hi_ps"] < 0


def test_ports_come_from_the_plan_ring_hold():
    plan = {"clock": {"ring_hold": {"write_edge": "fall", "write_fall_types": ["tB"]}},
            "partitions": [{"name": "A", "type": "tA"}, {"name": "B", "type": "tB"}],
            "ports": [{"id": "x", "src": {"part": "A"}, "dst": {"part": "B"}},
                      {"id": "y", "src": {"part": "B"}, "dst": {"part": "A"}}]}
    b = {"ports": {"x": {}, "y": {}}}
    assert CAB.write_fall_ports(b, plan) == {"x"}
    plan["clock"]["ring_hold"]["write_edge"] = "rise"
    assert CAB.write_fall_ports(b, plan) == set()
