"""LEC-RELAYHINT-1 (COORD 11-25): structural reset / start relay classes -> correspondence hints, default in lec.py.
s81_head hd_mesh: the earlier generator paired relays of different shift depth (u_srl_55 depth 4 with u_srl_0
depth 1); the induction dropped them and with them the u_lb reset-root alias, failing 9,556 SRAM pins.
    python3 -m pytest -q tools/die_plan/test_relay_hints.py"""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


rh = _load("relay_hints_ut", "relay_hints.py")

TOP = """
module other_mod(input wire clk); ot_dp_rrelay u_rrl_99 (.clk(clk), .d(x), .q(y)); endmodule
module top_ep(input wire clk, arst_n, start_i);
    wire rst_root_n, run_root;
    ot_dp_rrelay_ph u_rst_in (.clk(clk), .d(arst_n), .q(rst_root_n), .ph(ph));
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));  // depth 1
    ot_dp_rrelay u_srl_0 (.clk(clk), .d(run_root), .q(rn_0));        // run depth 1
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_rl_1));    // depth 2
    ot_dp_rrelay u_srl_1 (.clk(clk), .d(rn_0), .q(rn_1));
    ot_dp_rgate u_rrl_2 (.clk(clk), .d(rst_rl_1), .run(rn_1), .q(rst_n_t0));   // gated depth 3
    ot_dp_head_raw_export_pair u_rrl_5 (.clk(clk), .d(rst_root_n), .q(rst_rl_5), .export_q(ex5));  // depth 1
    ot_dp_rrelay u_rrl_6 (.clk(clk), .d(rst_rl_5), .q(rst_rl_6));    // depth 2
    ot_dp_rrelay u_srl_6 (.clk(clk), .d(run_root), .q(rn_6));
    ot_dp_rrelay u_srl_7 (.clk(clk), .d(rn_6), .q(rn_7));
    ot_dp_rgate u_rrl_7 (.clk(clk),
                         .d(rst_rl_6), .run(rn_7), .q(rst_n_t1));   // gated depth 3, multi-line
endmodule
"""


def test_classes_follow_depth_and_gating():
    rows = rh.relays(rh.module_text(TOP, "top_ep"))
    assert "u_rrl_99" not in rows and "u_rst_in" not in rows
    cl = rh.classes(rows)
    assert cl["u_rrl_0"] == cl["u_rrl_5"] and cl["u_rrl_1"] == cl["u_rrl_6"] and cl["u_rrl_2"] == cl["u_rrl_7"]
    assert cl["u_srl_0"] == cl["u_srl_6"] and cl["u_srl_1"] == cl["u_srl_7"]
    assert len({cl["u_rrl_0"], cl["u_rrl_1"], cl["u_rrl_2"], cl["u_srl_0"], cl["u_srl_1"]}) == 5
    hs = {e[1]: e[2][2] for e in rh.hints(rows)}
    assert hs["ff:u_dut.u_rrl_7.q"] == "ff:u_dut.u_rrl_2.q" and hs["ff:u_dut.u_rrl_5.export_q"] == "ff:u_dut.u_rrl_0.q"


def test_wrong_phase_hints_counted_and_replaced():
    rows = rh.relays(rh.module_text(TOP, "top_ep"))
    supplied = [["both", "ff:u_dut.u_srl_7.q", ["eq", "gold", "ff:u_dut.u_srl_0.q", 0]],   # depth 2 vs 1: wrong
                ["both", "ff:u_dut.u_rrl_6.q", ["eq", "gold", "ff:u_dut.u_rrl_1.q", 0]],   # right
                ["gold", "ff:u_dut.u_core.x[0]", ["const", 0]]]                            # not a relay: kept
    out, info = rh.rewrite(supplied, rows)
    assert info["supplied_relay"] == 2 and info["supplied_wrong_phase"] == 1
    assert ["gold", "ff:u_dut.u_core.x[0]", ["const", 0]] in out
    assert ["both", "ff:u_dut.u_srl_7.q", ["eq", "gold", "ff:u_dut.u_srl_0.q", 0]] not in out
    assert ["both", "ff:u_dut.u_srl_7.q", ["eq", "gold", "ff:u_dut.u_srl_1.q", 0]] in out


def test_lec_reads_top_module_relays_from_kit(tmp_path, monkeypatch):
    lec = _load("lec_relay_ut", "lec.py")
    (tmp_path / "rtl").mkdir()
    (tmp_path / "rtl" / "top.sv").write_text(TOP)
    env = {"VERILOG_FILES": "/work/rtl/top.sv"}
    rec = {}
    rows = lec.relay_class_rows(env, str(tmp_path), "top_ep", rec)
    assert len(rows) == 10 and rec["relay_cells"] == 10
    monkeypatch.setenv("OT_LEC_RELAY_HINTS", "0")
    assert lec.relay_class_rows(env, str(tmp_path), "top_ep", {}) == {}
    assert "OT_LEC_RELAY_HINTS" in lec.PROOF_OPTIONS


def test_hd_mesh_shape_cli(tmp_path, capsys):
    f = tmp_path / "t.sv"
    f.write_text(TOP)
    h = tmp_path / "h.json"
    h.write_text(json.dumps([["both", "ff:u_dut.u_srl_7.q", ["eq", "gold", "ff:u_dut.u_srl_0.q", 0]]]))
    assert rh.main([str(f), "--top", "top_ep", "--hints", str(h), "--out", str(tmp_path / "o.json")]) == 0
    info = json.loads(capsys.readouterr().out)
    assert info["supplied_wrong_phase"] == 1 and info["relays"] == 10
    assert json.loads((tmp_path / "o.json").read_text())


REPOINT = """
module rp_ep(input wire clk, arst_n, brst_n);
    wire rst_root_n, alt_root_n;
    ot_dp_rrelay_ph u_rst_in (.clk(clk), .d(arst_n), .q(rst_root_n), .ph(ph));
    ot_dp_rrelay_ph u_alt_in (.clk(clk), .d(brst_n), .q(alt_root_n), .ph(ph));
    ot_dp_rrelay u_rrl_4 (.clk(clk), .d(rst_root_n), .q(r4a));   ot_dp_rrelay u_rrl_40 (.clk(clk), .d(r4a), .q(r4));
    ot_dp_rrelay u_rrl_68 (.clk(clk), .d(rst_root_n), .q(r68a)); ot_dp_rrelay u_rrl_69 (.clk(clk), .d(r68a), .q(r68));
    ot_dp_rrelay u_rrl_172 (.clk(clk), .d(rst_root_n), .q(r172a)); ot_dp_rrelay u_rrl_173 (.clk(clk), .d(r172a), .q(r172));
    ot_dp_rrelay u_rrl_90 (.clk(clk), .d(alt_root_n), .q(r90a)); ot_dp_rrelay u_rrl_91 (.clk(clk), .d(r90a), .q(r90));
    ot_dp_rrelay u_rrl_174 (.clk(clk), .d(r172), .q(r174));
endmodule
"""


def test_repointed_reset_relays_pair_by_root_and_depth_only():
    """COORD 11-25 hd_mesh 22dcfc2f: reset_taps.tcl re-points a FIRM flop from one tap's relay to the nearest tap's
    relay (u_rrl_68 against u_rrl_172).  Same root + same depth -> one class, both hinted to one representative;
    a different root (same depth) or a different depth (same root) stays a separate class, and a supplied hint
    across either is counted wrong-phase and replaced, never kept."""
    rows = rh.relays(rh.module_text(REPOINT, "rp_ep"))
    cl = rh.classes(rows)
    assert cl["u_rrl_69"] == cl["u_rrl_173"] == cl["u_rrl_40"]                   # root rst_root_n, depth 2
    assert cl["u_rrl_91"] != cl["u_rrl_173"]                                      # other root, same depth
    assert cl["u_rrl_174"] != cl["u_rrl_173"] and cl["u_rrl_68"] != cl["u_rrl_69"]  # same root, other depth
    hs = {e[1]: e[2][2] for e in rh.hints(rows)}
    assert hs["ff:u_dut.u_rrl_69.q"] == hs["ff:u_dut.u_rrl_173.q"] == "ff:u_dut.u_rrl_40.q"
    assert "ff:u_dut.u_rrl_91.q" not in hs and "ff:u_dut.u_rrl_174.q" not in hs
    supplied = [["both", "ff:u_dut.u_rrl_173.q", ["eq", "gold", "ff:u_dut.u_rrl_69.q", 0]],   # right
                ["both", "ff:u_dut.u_rrl_91.q", ["eq", "gold", "ff:u_dut.u_rrl_69.q", 0]],    # root differs
                ["both", "ff:u_dut.u_rrl_174.q", ["eq", "gold", "ff:u_dut.u_rrl_173.q", 0]],  # depth differs
                ["both", "ff:u_dut.u_rrl_173.q", ["eq", "gold", "ff:u_dut.u_rrl_69.q", 1]]]   # inverted
    out, info = rh.rewrite(supplied, rows)
    assert info["supplied_relay"] == 4 and info["supplied_wrong_phase"] == 3
    pairs = {(e[1], e[2][2]) for e in out}
    assert ("ff:u_dut.u_rrl_91.q", "ff:u_dut.u_rrl_69.q") not in pairs
    assert ("ff:u_dut.u_rrl_174.q", "ff:u_dut.u_rrl_173.q") not in pairs
    assert all(e[2][3] == 0 for e in out)
