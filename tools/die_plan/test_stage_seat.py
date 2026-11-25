"""S81-STAGE-SEAT 11-25: stage_seat.py (OT_STAGE_SEAT knob, bound-RTL stage stems -> widened OT_RELAY_MID_RE) + gen_phys wiring."""
import re
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stage_seat as SS  # noqa: E402

RTL = """
module top(input clk);
    ot_dp_st #(.W(668)) u_bin_leafup_i0 (.clk(clk), .rst_n(rst_n), .d(a), .ea(b), .q(c), .eq(d));
    ot_dp_dly #(.W(669), .D(2)) u_lpad_leafup_i1 (.clk(clk), .d(x), .q(y));  // lane pad
    ot_dp_rrelay u_d14_u_r0_u_cf_rs_r63_s0 (.clk(clk), .d(p), .q(q));
    ot_s81_rly u_y_xo0_0 (.clk(clk), .d(p), .q(q));
    // ot_dp_st u_commented (.clk(clk));
endmodule
"""
BASE = r"^(.*[._]u_y_[A-Za-z0-9_]+)[.]"


def test_instances_skip_comments_and_relays():
    assert SS.stage_instances(RTL) == [("ot_dp_st", "u_bin_leafup_i0"), ("ot_dp_dly", "u_lpad_leafup_i1"),
                                       ("ot_dp_rrelay", "u_d14_u_r0_u_cf_rs_r63_s0")]


def test_widen_matches_stages_and_keeps_relays():
    rx = re.compile(SS.widen(BASE, [RTL]))
    for name, grp in [("top.u_y_xo0_0.q[3]$_DFF_P_", "top.u_y_xo0_0"), ("u_r0.u_y_es_p1_0.q[1]", "u_r0.u_y_es_p1_0"),
                      ("u_bin_leafup_i7.q[5]$_DFF_P_", "u_bin_leafup_i7"), ("top.u_lpad_leafup_i3.r[0][12]$_DFF_P_", "top.u_lpad_leafup_i3.r[0]"),
                      ("u_lpad_leafup_i3.q[4]", "u_lpad_leafup_i3.q"), ("u_d14_u_r0_u_cf_rs_r63_s5.q[0]", "u_d14_u_r0_u_cf_rs_r63_s5")]:
        m = rx.match(name)
        assert m and m.group(1) == grp, (name, m and m.group(1))
    for name in ("u_bin_leafup_i7_x.q[5]", "u_lpad_leafup_i3.q_pin", "u_foo.q[0]"):
        assert not rx.match(name), name


def test_widen_noop_without_stages_or_unknown_base():
    assert SS.widen(BASE, ["module m; endmodule"]) == BASE
    assert SS.widen(r"weird", [RTL]) == "weird"


def test_knob_precedence():
    assert SS.enabled({}, "t", "s81", env={}) is False or SS.DEFAULT_ON
    assert SS.enabled({}, "t", "s81", env={"OT_STAGE_SEAT": "1"}) is True
    assert SS.enabled({"stage_seat": True}, "t", "hbm", env={}) is True
    assert SS.enabled({"stage_seat": True}, "t", "s81", env={"OT_STAGE_SEAT": "0"}) is False
    assert SS.enabled({"stage_seat_types": ["ot_x"]}, "ot_x__t5", "hbm", env={}) is True
    assert SS.enabled({"stage_seat_types": ["ot_x"]}, "ot_y__t5", "hbm", env={}) is False


def test_exports():
    assert SS.exports(False) == []
    assert "export OT_RELAY_POLY = 1" in SS.exports(True)


def test_gen_phys_wiring(tmp_path, monkeypatch):
    import gen_phys as G
    f = tmp_path / "b.sv"
    f.write_text(RTL)
    P = types.SimpleNamespace(budgets={}, die={"name": "s81"})
    monkeypatch.delenv("OT_STAGE_SEAT", raising=False)
    monkeypatch.setattr(SS, "DEFAULT_ON", False)
    assert G._stage_seat_re(P, "t", [str(f)], BASE) == BASE                  # off: byte-identical
    monkeypatch.setenv("OT_STAGE_SEAT", "1")
    assert "u_bin_leafup_i" in G._stage_seat_re(P, "t", [str(f)], BASE)
    assert G._stage_seat_on(P, "t")
    monkeypatch.setenv("OT_STAGE_SEAT", "0")
    monkeypatch.setattr(SS, "DEFAULT_ON", True)
    assert not G._stage_seat_on(P, "t")
    monkeypatch.delenv("OT_STAGE_SEAT")
    assert G._stage_seat_on(P, "t")                                          # default-on die
    assert not G._stage_seat_on(types.SimpleNamespace(budgets={}, die={"name": "hbm"}), "t")
