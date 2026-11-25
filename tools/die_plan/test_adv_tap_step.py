"""pytest: ADV-TAP-STEP (HEAD W6 hd_lep0N: neighbour tap offsets 125 ps apart on a 42 ps setup budget)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_tap_step as A  # noqa: E402


def plan(offs, extra_tap=False):
    taps = [{"name": "clk", "xy": [0.0, 0.0]}, {"name": "clk_t1", "xy": [100.0, 0.0]}, {"name": "clk_t2", "xy": [200.0, 0.0]}]
    if extra_tap:
        taps.append({"name": "clk_t3", "xy": [300.0, 0.0]})
    t = {"clock": {"taps": taps}, "hard_cores": [{"inst": "u_m", "origin_um": [90.0, 10.0], "outline_um": [20.0, 20.0]}]}
    return {"clock": {"tap_offset": {"per_port_ps": {"t": {n: {"TT": v, "FF": v * 0.8} for n, v in offs.items()}}}},
            "partition_types": {"t": t, "u": {"clock": {"taps": taps}}}}


def test_smooth_table_passes_and_step_fails():
    ok = plan({"clk": 0.0, "clk_t1": 20.0, "clk_t2": 40.0})
    lines = A.findings(ok, "p")
    assert not [x for x in lines if x.startswith("WARN ADV-TAP-STEP t:")]
    assert any("UNPRICED" in x and " u" in x for x in lines)
    bad = plan({"clk": 0.0, "clk_t1": 125.0, "clk_t2": 130.0})
    line = [x for x in A.findings(bad, "p") if x.startswith("WARN ADV-TAP-STEP t:")][0]
    assert "max 130.0" in line and "2 TT neighbour tap pairs" in line


def test_missing_row_fails():
    res, _ = A.check(plan({"clk": 0.0, "clk_t1": 10.0, "clk_t2": 20.0}, extra_tap=True), ["t"])
    assert res["t"]["missing"] == ["clk_t3"]
