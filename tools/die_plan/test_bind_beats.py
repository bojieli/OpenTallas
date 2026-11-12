"""HBM-QQBIND-1 (2026-11-12): bind-emitted 2/4-beat lane endpoints (ot_hbm_hw_lane_tx / _rx).

python3 -m pytest tools/die_plan/test_bind_beats.py   (needs Yosys like test_bind.py)

  * a plan without beat_endpoint binds byte-identically, also when its lanes carry DEC12 beats / word_bits (leaf-
    serialised meaning, e.g. HBM L74 tkx): no wrapper, same RTL;
  * a lane with beat_endpoint "bind" gets TX / RX wrappers, a ceil(W / beats) + 1 physical bus (ft stations included),
    lands at word_cycles = cycles + beats - 1, and the independent verify proof still matches every sink;
  * a bind-beat lane without its P1/P2 bit classes, or whose port is too narrow, fails closed.
"""
import json
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_bind import EX, plan_copy, report, run, verify, pytestmark  # noqa: E402,F401


def _rtl(out):
    return {f.name: f.read_text() for f in sorted((out / "rtl").glob("*.sv"))}


def _beats(p, beats=2, endpoint=True, classes=True, port_w=None):
    """a0y (A0 -> F station -> A1) and a1y (A1 -> A0): the 8-bit u_b.o bundle as one word of `beats` beats.  Both
    y_o lanes of type ta take the same form so A0 / A1 stay one type."""
    pw = port_w if port_w is not None else -(-8 // beats) + 1
    for ln in p["lanes"]:
        if ln["id"] in ("a0y", "a1y"):
            ln.update(beats=beats, word_bits=8)
            if endpoint:
                ln["beat_endpoint"] = "bind"
            if classes:
                ln["beat_classes"] = {"control": [], "payload": [], "evidence": "test: u_b.o is a level"}
    for x in p["ports"]:
        if x["id"] in ("a0y__0", "a0y__1", "a1y__0"):
            x["width"] = pw
    for b in p["partition_types"]["ta"]["buses"]:
        if b["name"] in ("y_o", "x_i"):
            b["width"] = pw
    for s in p["partition_types"]["tf"]["ft_slots"]:
        s["width"] = pw
    for lid in ("a0y", "a1y"):
        lat = p["latency"]["lanes"][lid]
        lat.update(beats=beats, word_cycles=lat["cycles"] + beats - 1)


def test_no_beat_plan_binds_unchanged(tmp_path):
    """no beat_endpoint -> byte-identical bind, even with DEC12 beats fields on the lanes"""
    base, dec12 = tmp_path / "base", tmp_path / "dec12"
    assert run(EX / "die_plan_lanes.json", base, "elab", "bind") == 0

    def edit(p):
        for ln in p["lanes"]:
            if ln["id"] == "a1y":
                ln.update(beats=2, word_bits=15)     # leaf-serialised meaning: ceil(15/2)+1 = 9 > 8 is not the bind's
    assert run(plan_copy(tmp_path, "die_plan_lanes.json", edit), dec12, "elab", "bind") == 0
    a, b = _rtl(base), _rtl(dec12)
    assert a.keys() == b.keys() and a == b
    assert not any("ot_hbm_hw_lane" in t for t in a.values())
    assert not any("ot_hbm_hw_lane" in f for f in report(base)["extra_lib"])


@pytest.mark.parametrize("beats", [2, 4])
def test_bind_beat_lane_wrappers(tmp_path, beats):
    out = tmp_path / "o"
    plan = plan_copy(tmp_path, "die_plan_lanes.json", lambda p: _beats(p, beats))
    assert run(plan, out, "elab", "bind", "verify") == 0, report(out)["errors"][:5]
    r, v = report(out), verify(out)
    assert r["n_errors"] == 0 and r["lanes"]["unplanned_bits"] == 0
    assert v["verdict"] == "PASS" and v["counts"]["mismatched"] == 0 and v["counts"]["matched"] == 64
    if v["lint"].get("ran"):
        assert v["lint"]["errors"] == 0
    pw = -(-8 // beats) + 1
    rtl = _rtl(out)
    ta, tf = rtl["bt_ta.sv"], rtl["bt_tf.sv"]
    # TX on y_o (its beat register is the out-boundary register; epoch keeps an ot_dp_st), RX after u_bin_ on x_i
    assert f"output wire [{pw}:0] y_o" in ta and f"input  wire [{pw}:0] x_i" in ta
    assert re.search(rf"ot_hbm_hw_lane_tx #\(\.W\(8\), \.HW\(1\), \.BEATS\({beats}\), \.CONTROL_MASK\(8'h0\), "
                     rf"\.PAYLOAD_MASK\(8'h0\)\) u_btx_y_o \(.*\.b_o\(y_o\[{pw - 2}:0\]\), \.f_o\(y_o\[{pw - 1}\]\)", ta)
    assert f"ot_dp_st #(.W(1)) u_bout_y_o (.clk(clk), .rst_n(rst_n), .d(rst_n), .ea(rst_n), .q(), .eq(y_o[{pw}]))" in ta
    assert f"ot_dp_st #(.W({pw})) u_bin_x_i" in ta and "u_brx_x_i" in ta and ".q(x_i_q)" in ta
    assert "ot_dp_st #(.W(8)) u_bout_y_o" not in ta
    # the ft station carries the physical beat bus
    assert f"input  wire [{pw}:0] y_i" in tf and f"ot_dp_st #(.W({pw}))" in tf
    # the other buses of the plan are untouched
    assert "ot_dp_st #(.W(8)) u_bout_ys_o" in ta
    assert "ot_bus_gear.sv" in "".join(r["extra_lib"]) and "ot_hbm_hw_lane.sv" in "".join(r["extra_lib"])
    lat = {b["lane"]: b for b in json.loads((out / "bind_latency.json").read_text())["buses"]}
    assert lat["a0y"]["beats"] == beats and lat["a0y"]["port_width"] == pw
    assert lat["a0y"]["bound_stages"] == 3 and lat["a0y"]["word_cycles"] == 3 + beats - 1
    assert lat["a1y"]["word_cycles"] == 2 + beats - 1
    assert "beats" not in lat["a0s"]


def test_bind_beat_lane_needs_classes(tmp_path):
    out = tmp_path / "o"
    run(plan_copy(tmp_path, "die_plan_lanes.json", lambda p: _beats(p, 2, classes=False)), out, "elab", "bind")
    assert any(e.startswith("LANE_BEAT_CLASSES a0y") for e in report(out)["errors"])


def test_bind_beat_lane_port_too_narrow(tmp_path):
    out = tmp_path / "o"
    run(plan_copy(tmp_path, "die_plan_lanes.json", lambda p: _beats(p, 2, port_w=4)), out, "elab", "bind")
    assert any(e.startswith("LANE_BEATS a0y") and "need port width 5" in e for e in report(out)["errors"])
