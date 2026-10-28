"""METHODOLOGY 12.4a b2 data droop derate per class (OWNER 10-27): fractions, setup-only charge in the shared die STA
model, the control (old flat +5.1 % reproduced, 'none' unchanged), netlist/SPEF wire-class classification and the
die_ci / signoff Tcl."""
import json

import data_droop as DD
import die_ci as C
import die_sta_related as R

REG = dict(clkq_max_wire_ps=68.0, clkq_min_nowire_ps=46.5, setup_ps=5.6, hold_ps=22.2)
M = DD.margins()


def _taps():
    return {"a": dict(late_ps=1000.0, early_ps=990.0, cppr_node="h0"),
            "b": dict(late_ps=1050.0, early_ps=1040.0, cppr_node="h0")}


def test_fractions_owner_table_and_flat_control():
    assert DD.fracs(M, "class", "TT") == {"logic": 0.10, "wire": 0.05}
    assert DD.fracs(M, "class", "FF") == {"logic": 0.08, "wire": 0.04}
    # the old stated term = die_ci ir factor - 1 (5 % drop x 1.022) on every data cell
    f = DD.fracs(M, "flat", "TT")
    assert f["logic"] == f["wire"] == round(C.ir_factor(M)[0] - 1.0, 4) == 0.0511
    assert DD.fracs(M, "none", "TT") == {"logic": 0.0, "wire": 0.0}
    # margins without a data_droop block (pre-b2) still give the owner table in class mode
    m0 = {k: v for k, v in M.items() if k != "data_droop"}
    assert DD.fracs(m0, "class", "TT") == {"logic": 0.10, "wire": 0.05}


def test_declared_register_setup_only_and_control():
    taps, rng = _taps(), {"h0": 10.0, "h": 30.0}
    pairs = [("a", "b", "p"), ("b", "a", "p")]
    base = R.time_class(pairs, taps, rng, REG, 20.0, 833.333, 60.0, 25.0)
    none = R.time_class(pairs, taps, rng, REG, 20.0, 833.333, 60.0, 25.0, dd=DD.fracs(M, "none", "TT"))
    flat = R.time_class(pairs, taps, rng, REG, 20.0, 833.333, 60.0, 25.0, dd=DD.fracs(M, "flat", "TT"))
    cls = R.time_class(pairs, taps, rng, REG, 20.0, 833.333, 60.0, 25.0, dd=DD.fracs(M, "class", "TT"))
    # control: option off reproduces the old numbers; flat reproduces the old +5.1 % data term on clk->Q exactly
    assert none["worst_setup_slack_ps"] == base["worst_setup_slack_ps"]
    assert flat["worst_setup_slack_ps"] == round(base["worst_setup_slack_ps"] - 0.0511 * 68.0, 2)
    assert cls["worst_setup_slack_ps"] == round(base["worst_setup_slack_ps"] - 0.10 * 68.0, 2)
    assert cls["data_droop_setup_max_ps"] == 6.8 and "data_droop_setup_max_ps" not in base
    # NEVER credited to hold
    for r in (none, flat, cls):
        assert r["worst_hold_slack_ps"] == base["worst_hold_slack_ps"]
        assert r["hold_neg_pairs"] == base["hold_neg_pairs"]


def test_real_view_etm_data_parts_and_wire_class():
    taps, rng = _taps(), {"h0": 10.0, "h": 30.0}
    etm = dict(clock_tree_path_ps={"max_clock_tree_path": 250.0, "min_clock_tree_path": 240.0})
    core = dict(name="core:c", real=True, lat_late=0.0, lat_early=0.0, clkq_max=380.0, clkq_min=370.0, setup=-200.0,
                hold=125.0, etm=etm)
    bud = R.budget_model(REG, 250.0)
    views = {"a": [core], "b": [core]}
    fr = DD.fracs(M, "class", "TT")
    # launch 380 - 250 = 130 ps data, capture -200 + 240 = 40 ps internal input path -> 0.10 x 170
    assert abs(DD.model_late_ps(core, core, fr) - 17.0) < 1e-9
    assert abs(DD.model_late_ps(bud, bud, fr) - 6.8) < 1e-9
    # wire class segments a model declares (repeated M8/M9 stages) take the wire fraction
    rep = dict(bud, wire_max_ps=200.0)
    assert abs(DD.model_late_ps(rep, bud, fr) - (6.8 + 0.05 * 200.0)) < 1e-9
    base = R.time_class([("a", "b", "p")], taps, rng, REG, 20.0, 833.333, 60.0, 25.0, views=views)
    cls = R.time_class([("a", "b", "p")], taps, rng, REG, 20.0, 833.333, 60.0, 25.0, views=views, dd=fr)
    assert cls["real_view"]["worst_setup_slack_ps"] == round(base["real_view"]["worst_setup_slack_ps"] - 17.0, 2)
    assert cls["real_view"]["worst_hold_slack_ps"] == base["real_view"]["worst_hold_slack_ps"]


NET = """module top(clk, a, y);
input clk; input a; output y;
wire n1, n2, n3, n4;
DFFHQNx1_ASAP7_75t_R r0 (.CLK(clk), .D(a), .QN(n1));
BUFx12f_ASAP7_75t_R rep1 (.A(n1), .Y(n2));
BUFx2_ASAP7_75t_R b_short (.A(n2), .Y(n3));
NAND2xp5_ASAP7_75t_R g1 (.A(n3), .B(a), .Y(n4));
INVx4_ASAP7_75t_R \\rep\\[2\\] (.A(n4), .Y(y));
endmodule
"""
SPEF = """*SPEF "IEEE 1481-1998"
*DESIGN "top"
*C_UNIT 1 FF
*R_UNIT 1 OHM
*NAME_MAP
*1 n2
*2 n3
*3 n4
*4 rep[2]
*5 y
*D_NET n1 3.0
*CONN
*I r0:QN O
*I rep1:A I
*END
*D_NET *1 85.0
*CONN
*I rep1:Y O
*I b_short:A I
*END
*D_NET *2 6.0
*CONN
*I b_short:Y O
*I g1:A I
*END
*D_NET *3 90.0
*CONN
*I g1:Y O
*I *4:A I
*END
*D_NET *5 0.05
*CONN
*I *4:Y O
*P y O
*END
"""


def test_classify_netlist_spef(tmp_path):
    (tmp_path / "n.v").write_text(NET)
    (tmp_path / "n.spef").write_text(SPEF)
    r = DD.classify(tmp_path / "n.v", tmp_path / "n.spef", M)
    # repeater master on an 85 fF net = wire; short buffer, NAND on a long net, flop = logic
    assert r["wire"] == ["rep1"] and r["n_cells"] == 5 and r["n_logic"] == 4
    sp = SPEF.replace("*D_NET *5 0.05", "*D_NET *5 0.12").replace("*C_UNIT 1 FF", "*C_UNIT 1 PF")
    sp = sp.replace("*D_NET n1 3.0", "*D_NET n1 0.003").replace("*D_NET *1 85.0", "*D_NET *1 0.085")
    sp = sp.replace("*D_NET *2 6.0", "*D_NET *2 0.006").replace("*D_NET *3 90.0", "*D_NET *3 0.09")
    (tmp_path / "p.spef").write_text(sp)
    r2 = DD.classify(tmp_path / "n.v", tmp_path / "p.spef", M)
    # PF units: escaped/mapped inverter rep[2] drives 120 fF -> wire too
    assert r2["wire"] == ["rep1", "rep[2]"]


def test_derate_tcl_late_data_only():
    t = DD.derate_tcl(DD.fracs(M, "class", "TT"), ["rep1", "rep[2]"])
    lines = t.strip().splitlines()
    assert lines[0] == "set_timing_derate -late -data -cell_delay 1.1000"
    assert lines[1].startswith("set_timing_derate -late -data -cell_delay 1.0500 [get_cells -quiet [list {rep1} {rep\\[2\\]}]")
    assert "-early" not in t and "-clock" not in t


def test_die_ci_class_vs_old_flat_control():
    d = C.derates(M)
    assert d["cell_late"] == 1.1037 and d["data_cell_late"] == round(1.05 * 1.10, 4) and d["data_wire_late"] == round(1.05 * 1.05, 4)
    t = C.derate_tcl(M)
    assert "set_timing_derate -late -clock -cell_delay 1.1037" in t          # clock: OCV x IR unchanged here
    assert "set_timing_derate -late -data -cell_delay 1.1550" in t           # data: OCV x (1 + 10 %)
    assert "set_timing_derate -early -cell_delay 0.9500" in t                 # early unchanged: no hold credit
    # control: margins without the b2 block reproduce the old flat Tcl byte for byte
    m0 = json.loads(json.dumps({k: v for k, v in M.items() if k != "data_droop"}))
    t0 = C.derate_tcl(m0)
    assert t0 == ("# DIE-CI margins (tools/die_plan/die_ci_margins.json): OCV x IR, on top of the AGENTS.md uncertainty\n"
                  "set_timing_derate -late -cell_delay 1.1037\nset_timing_derate -early -cell_delay 0.9500\n"
                  "set_timing_derate -late -net_delay 1.0300\nset_timing_derate -early -net_delay 0.9700\n")
    assert "data_cell_late" not in C.derates(m0)
    assert C.DEFAULT_MARGINS["data_droop"]["late_frac"] == M["data_droop"]["late_frac"]


def test_negative_droop_rejected():
    import pytest
    m = json.loads(json.dumps(M))
    m["data_droop"]["late_frac"]["logic"]["TT"] = -0.01
    with pytest.raises(SystemExit):
        C.check_margins(m)


def test_signoff_session_droop_block_info_only():
    import signoff as S
    t0 = S.session_tcl("tt", [], "/base/6_final.spef")
    dt = DD.derate_tcl(DD.fracs(M, "class", "TT"), ["wire12"])
    t1 = S.session_tcl("tt", [], "/base/6_final.spef", droop=dt)
    assert "@DROOP665@" not in t0 and "DROOP665" not in t0          # default: session unchanged
    blk = t1.split("so OCV5_WNS_MIN")[1]
    assert dt in t1 and "so DROOP665_WNS_MAX" in blk
    # the block undoes its derate before the pair-skew / clock sections; t1 minus the block == t0
    i, j = t1.index("# ---- 12.4a b2 0.665 V"), t1.index("unset_timing_derate\n", t1.index("so DROOP665_WNS_MAX"))
    assert t1[:i] + t1[j + len("unset_timing_derate\n"):] == t0
    kv = {"DROOP665_WNS_MAX": "-3.5", "DONE": "1"}
    assert S.corner_result(dict(kv=kv, ck=[], blocks={}))["droop665_wns_max"] == -3.5
    assert "droop665_wns_max" not in S.corner_result(dict(kv={"DONE": "1"}, ck=[], blocks={}))
    assert "data_droop.py" in S.SIGNOFF_BUNDLE
