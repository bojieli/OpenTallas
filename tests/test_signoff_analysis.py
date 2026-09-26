"""Tests for tools/signoff_analysis.py (sign-off power, IR and clock analysis)
and the sign-off options of tools/run_abi3_physical.py."""
from __future__ import annotations

import itertools
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import signoff_analysis as S  # noqa: E402
import run_abi3_physical as P  # noqa: E402


def _py(expr: str, env: dict[str, int], table: dict[str, str]) -> int:
    for k, v in table.items():
        expr = expr.replace(k, v)
    for name in sorted(env, key=len, reverse=True):
        expr = re.sub(rf"\b{name}\b", str(bool(env[name])), expr)
    return int(bool(eval(expr)))  # noqa: S307 - generated from a fixed grammar


def _eval_verilog(expr: str, env: dict[str, int]) -> int:
    # the translation is fully parenthesised, so Python's precedence is moot
    return _py(expr, env, {"1'b0": "False", "1'b1": "True", "~": " not ", "&": " and ", "|": " or ",
                           "^": " != "})


def _eval_liberty(expr: str, env: dict[str, int]) -> int:
    # Liberty precedence (! > * > +) is Python's (not > and > or)
    return _py(expr, env, {"!": " not ", "*": " and ", "+": " or "})


@pytest.mark.parametrize("fn", [
    "(!A1 * !A2) + (!B)",
    "(A * !B) + (!A * B)",
    "(A1 * B1 * C1) + (A1 * B2 * C1) + (A2 * B1 * C1)",
    "!((A + B) * C)",
    "(!A * !B * !CI) + (A * B * !CI)",
])
def test_liberty_functions_translate_exactly(fn):
    names = sorted(set(re.findall(r"[A-Z][A-Z0-9]*", fn)))
    v = S.liberty_expr_to_verilog(fn)
    for bits in itertools.product((0, 1), repeat=len(names)):
        env = dict(zip(names, bits))
        assert _eval_verilog(v, env) == _eval_liberty(fn, env), (fn, env)


def test_postfix_not_and_juxtaposition():
    assert _eval_verilog(S.liberty_expr_to_verilog("A' B"), {"A": 0, "B": 1}) == 1
    assert _eval_verilog(S.liberty_expr_to_verilog("A' B"), {"A": 1, "B": 1}) == 0
    with pytest.raises(ValueError):
        S.liberty_expr_to_verilog("A * ")


ASYNC_FF = """
  cell (DFFASR_T) {
    pin (QN) { direction : output; function : "IQN"; }
    pin (CLK) { direction : input; }
    pin (D) { direction : input; }
    pin (RESETN) { direction : input; }
    pin (SETN) { direction : input; }
    ff (IQN,IQNN) {
      clear : "!SETN";
      clear_preset_var1 : L;
      clocked_on : "CLK";
      next_state : "!D";
      preset : "!RESETN";
    }
  }
  cell (ICG_T) {
    statetable ("CLK ENA SE", "IQ") { table : "L L L : - : L"; }
    pin (IQ) { direction : internal; internal_node : "IQ"; }
    pin (GCLK) { direction : output; state_function : "CLK & IQ"; }
    pin (CLK) { direction : input; }
    pin (ENA) { direction : input; }
    pin (SE) { direction : input; }
  }
  cell (NAND_T) {
    pin (Y) { direction : output; function : "!(A * B)"; }
    pin (A) { direction : input; }
    pin (B) { direction : input; }
  }
"""


def test_cell_models_cover_async_flop_clock_gate_and_logic(tmp_path):
    lib = tmp_path / "t.lib"
    lib.write_text("library (t) {" + ASYNC_FF + "}")
    out = tmp_path / "cells.v"
    r = S.write_cell_models([lib], out)
    assert r == {"models": 3, "skipped": [], "missing": []}
    text = out.read_text()
    assert "always @(posedge CLK or negedge SETN or negedge RESETN)" in text
    # both controls asserted resolve by clear_preset_var1 (L -> 0)
    assert "if ((!SETN) && (!RESETN)) IQN <= 1'b0;" in text
    assert "always @* if (!CLK) IQ = ENA | SE;" in text
    assert "assign GCLK = (CLK & IQ);" in text
    if shutil.which("verilator"):
        lint = subprocess.run(["verilator", "--lint-only", "-Wno-fatal", "-Wno-DECLFILENAME", "-Wno-UNUSED",
                               str(out), "--top-module", "DFFASR_T"], capture_output=True, text=True)
        assert "%Error" not in lint.stderr


def test_netlist_cell_types_and_dummy_parameters(tmp_path):
    net = tmp_path / "n.v"
    net.write_text("module top (a,\n    y);\n input a;\n output y;\n wire w;\n"
                   " INVx1_ASAP7_75t_R _1_ (.A(a),\n    .Y(w));\n BUFx2_ASAP7_75t_R \\u_x.q$_DFF_  (.A(w),\n"
                   "    .Y(y));\nendmodule\n")
    assert S.netlist_cell_types(net) == {"INVx1_ASAP7_75t_R", "BUFx2_ASAP7_75t_R"}
    out = tmp_path / "o.v"
    assert S.netlist_accepting_params(net, out, ["K", "IW", "K"]) == ["IW", "K"]
    lines = out.read_text().splitlines()
    assert lines[2] == " parameter integer IW = 0;" and lines[3] == " parameter integer K = 0;"


def test_rtl_param_overrides(tmp_path):
    f = tmp_path / "p.sv"
    f.write_text("ot_hdc_select #(.K(K), .VW(32), .IW(16), .ORDER(1)) u_sel (.clk(clk));\n"
                 "ot_hdc_actquant u_aq (.clk(clk));\n")
    assert S.rtl_param_overrides([f], "ot_hdc_select") == {"K", "VW", "IW", "ORDER"}
    assert S.rtl_param_overrides([f], "ot_hdc_actquant") == set()


def test_gate_level_bench_strips_hierarchy_peeks_and_override():
    bench = (ROOT / "rtl/test/tb_hdc_core.sv").read_text()
    text, removed = S.gate_level_bench(bench, "ot_hdc_core")
    assert "ot_hdc_core dut (" in text and not re.search(r"ot_hdc_core\s*#", text)
    assert not re.search(r"\bdut\.", text)
    assert len(removed) == 4
    # the checks that decide PASS survive
    assert "HDC token=%0d" in text and '$display("PASS")' in text
    v41 = (ROOT / "rtl/test/tb_hdc_core_v41.sv").read_text()
    t41, r41 = S.gate_level_bench(v41, "ot_hdc_core_v41")
    assert not re.search(r"\bdut\.", t41) and len(r41) == 3


SESSION_TEXT = """
SIGNOFF power.total.total_w=0.0125
SIGNOFF power.clock.total_w=0.001
SIGNOFF timing.setup_wns_s=-1.0e-11
core_clk period_min = 0.91 fmax = 1098.64
 0.0089 setup skew
-0.0120 hold skew
 0.0686  0.0784 latency
IRSOURCE PINS
########## IR report #################
Net              : VDD
Corner           : default
Total power      : 1.25e-02 W
Supply voltage   : 7.00e-01 V
Worstcase voltage: 6.98e-01 V
Average voltage  : 7.00e-01 V
Average IR drop  : 3.86e-04 V
Worstcase IR drop: 1.77e-03 V
Percentage drop  : 0.25 %
######################################
########## EM analysis ###############
Net                : VDD
Corner             : default
Maximum current    : 1.80e-04 A
Average current    : 1.25e-06 A
Number of resistors: 77266
######################################
"""


def test_parse_session():
    p = S.parse_session(SESSION_TEXT)
    assert p["power.total.total_w"] == 0.0125
    assert p["min_period"] == [{"clock": "core_clk", "period_min_ns": 0.91, "fmax_mhz": 1098.64}]
    assert p["skew"] == {"setup": 0.0089, "hold": -0.012}
    assert p["latency"] == [{"min_ns": 0.0686, "max_ns": 0.0784}]
    (ir,) = p["ir"]
    assert ir["source_type"] == "PINS" and ir["net"] == "VDD"
    assert ir["worst_ir_drop_v"] == 1.77e-3 and ir["resistors"] == 77266


def test_session_script_has_every_stage():
    s = S.session_script("/r", "/o", "SS", saif="/a/x.saif", saif_scope="dut", groups=["u_me."],
                         derate=0.05, ir_sources=("PINS", "BUMPS"))
    assert "asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib" in s
    assert "set ::so_vdd 0.63" in s
    assert "read_saif -scope $::so_saif_scope $::so_saif" in s
    assert "set_timing_derate -early" in s and "unset_timing_derate" in s
    assert s.count("analyze_power_grid") == 4 and "-allow_reuse" not in s
    assert "report_clock_skew" in s


def test_em_and_ir_postprocessing(tmp_path):
    em = tmp_path / "em.csv"
    em.write_text("Node0 Layer,Node0 X location,Node0 Y location,Node1 Layer,Node1 X location,Node1 Y location,"
                  "Current\nM2,1,1,M2,2,1,3.6e-05\nM2,2,1,M2,3,1,1.0e-06\nM5,1,1,M5,1,2,6.0e-05\n"
                  "M5,1,1,M6,1,1,1.0e-04\n")
    r = S.em_hotspots(em, top=2)
    assert r["per_layer"]["M2"]["max_ma_per_um"] == pytest.approx(2.0)
    assert r["per_layer"]["M2"]["over_assumed_limit"] is True
    assert r["per_layer"]["M5"]["over_assumed_limit"] is False
    assert [h["layer"] for h in r["hotspots"]] == ["M2", "M5"]
    ir = tmp_path / "ir.csv"
    ir.write_text("Instance,Terminal,Layer,X location,Y location,Voltage\n"
                  "u_me.a,VDD,M1,0,0,0.690\nu_me.b,VDD,M1,0,0,0.698\nu_su.c,VDD,M1,0,0,0.700\n"
                  "FILLER_1,VDD,M1,0,0,0.699\n")
    g = S.ir_group_stats(ir, ["u_me.", "u_su."], "VDD")
    assert g["u_me."]["worst_drop_v"] == pytest.approx(0.010)
    assert g["u_me."]["average_drop_v"] == pytest.approx(0.006)
    assert g["__physical__"]["terminals"] == 1


VCD = """$timescale 1ps $end
$scope module tb $end
$var wire 1 ! clk $end
$scope module dut $end
$var wire 1 # a $end
$var wire 3 $ bus [2:0] $end
$scope module sub $end
$var wire 1 % u_me.q $end
$upscope $end
$upscope $end
$upscope $end
$enddefinitions $end
#0
0!
0#
b000 $
0%
#450
1!
1#
b101 $
#900
0!
0#
b1 $
1%
#1350
1!
#1800
"""


@pytest.mark.skipif(shutil.which("g++") is None, reason="needs g++")
def test_vcd2saif_counts_toggles_and_time(tmp_path):
    exe = S.build_vcd2saif(tmp_path)
    vcd = tmp_path / "t.vcd"
    vcd.write_text(VCD)
    out = tmp_path / "t.saif"
    subprocess.run([str(exe), str(vcd), str(out), "tb.dut", "0"], check=True, capture_output=True)
    text = out.read_text()
    assert "(DURATION 1800)" in text and "(TIMESCALE 1ps)" in text and "(DIVIDER / )" in text
    assert "(INSTANCE dut" in text and "(INSTANCE sub" in text
    assert "(a (T0 1350) (T1 450) (TX 0) (TC 2))" in text
    assert "(bus\\[0\\] (T0 450) (T1 1350) (TX 0) (TC 1))" in text   # 0 -> 1 -> 1
    assert "(bus\\[2\\] (T0 1350) (T1 450) (TX 0) (TC 2))" in text   # 0 -> 1 -> 0 (b1 zero-extends)
    assert "(u_me\\.q (T0 900) (T1 900) (TX 0) (TC 1))" in text
    assert "clk" not in text   # outside the scope


def test_design_nickname_default_unchanged_and_tagged():
    assert P.design_nickname("ot_hdc_core", "asap7") == "opentallas_ot_hdc_core_asap7"
    assert P.design_nickname("ot_hdc_core", "asap7", "signoff") == "opentallas_ot_hdc_core_asap7_signoff"
    with pytest.raises(ValueError):
        P.design_nickname("ot_hdc_core", "asap7", "bad tag")
    args = P.build_parser().parse_args(["--view", "asap7", "--clock-period-ns", "1", "--output", "x"])
    assert args.nickname_tag is None


def test_expand_net_saif_to_cell_pins(tmp_path):
    net = tmp_path / "n.v"
    net.write_text("module top (clk,\n    a,\n    y);\n input clk;\n input [1:0] a;\n output y;\n"
                   " wire _1_;\n wire \\u_me.q ;\n"
                   " NAND2x1_ASAP7_75t_R _5_ (.A(a[0]),\n    .B(a[1]),\n    .Y(_1_));\n"
                   " DFFHQNx1_ASAP7_75t_R \\u_me.q$_DFF_P_  (.CLK(clk),\n    .D(_1_),\n    .QN(\\u_me.q ));\n"
                   " INVx1_ASAP7_75t_R _6_ (.A(\\u_me.q ),\n    .Y(y));\n"
                   " TIEHIx1_ASAP7_75t_R _7_ (.H(1'b1));\nendmodule\n")
    saif = tmp_path / "n.saif"
    saif.write_text('(SAIFILE\n(DESIGN "dut")\n(DIVIDER / )\n(TIMESCALE 1ps)\n(DURATION 100)\n(INSTANCE dut\n'
                    '  (NET\n    (clk (T0 50) (T1 50) (TX 0) (TC 20))\n    (a\\[0\\] (T0 60) (T1 40) (TX 0) (TC 3))\n'
                    '    (a\\[1\\] (T0 70) (T1 30) (TX 0) (TC 2))\n    (y (T0 10) (T1 90) (TX 0) (TC 1))\n'
                    '    (_1_ (T0 80) (T1 20) (TX 0) (TC 4))\n    (u_me\\.q (T0 90) (T1 10) (TX 0) (TC 1))\n  )\n)\n)\n')
    out = tmp_path / "p.saif"
    st = S.expand_saif_to_pins(saif, net, out)
    assert st["ports_written"] == 4 and st["instances"] == 3 and st["pins_written"] == 8
    text = out.read_text()
    # the flop instance keeps '.' and '$' raw (what OpenSTA's reader matches); brackets escaped
    assert "(INSTANCE u_me.q$_DFF_P_" in text
    assert "(QN (T0 90) (T1 10) (TX 0) (TC 1))" in text
    assert "(a\\[1\\] (T0 70) (T1 30) (TX 0) (TC 2))" in text
    assert "_7_" not in text   # a tie cell has no activity to carry


def test_rtl_without_modules_keeps_helpers(tmp_path):
    src = ROOT / "rtl/hdc/v41/ot_hdc_blockdot.sv"
    out = S.rtl_without_modules(src, {"ot_hdc_blockdot"}, tmp_path)
    mods = re.findall(r"^\s*module\s+(\w+)", out.read_text(), re.M)
    assert mods == ["ot_hdc_v41_csa"]
    assert S.rtl_without_modules(ROOT / "rtl/hdc/ot_hdc_fpu.sv", {"ot_hdc_blockdot"}, tmp_path) == \
        ROOT / "rtl/hdc/ot_hdc_fpu.sv"


def test_rtl_register_names_map_onto_routed_flops(tmp_path):
    net = tmp_path / "n.v"
    net.write_text("module top (clk,\n    y);\n input clk;\n output y;\n"
                   " DFFHQNx1_ASAP7_75t_R \\u_d.genblk1.g_line.line[3]$_DFF_P_  (.CLK(clk),\n    .D(y),\n"
                   "    .QN(_1_));\n"
                   " DFFHQNx1_ASAP7_75t_R \\st[0]$_DFFE_PN0P_  (.CLK(clk),\n    .D(y),\n    .QN(_2_));\n"
                   " DFFHQNx1_ASAP7_75t_R \\gone[0]$_DFF_P_  (.CLK(clk),\n    .D(y),\n    .QN(_3_));\n"
                   "endmodule\n")
    saif = tmp_path / "r.saif"
    saif.write_text('(SAIFILE\n(DESIGN "dut")\n(DIVIDER / )\n(TIMESCALE 1ps)\n(DURATION 100)\n(INSTANCE dut\n'
                    '  (NET\n    (clk (T0 50) (T1 50) (TX 0) (TC 20))\n    (y (T0 50) (T1 50) (TX 0) (TC 7))\n'
                    '    (st\\[0\\] (T0 70) (T1 30) (TX 0) (TC 4))\n  )\n'
                    '  (INSTANCE u_d\n    (INSTANCE g_line\n      (NET\n'
                    '        (line\\[3\\] (T0 90) (T1 10) (TX 0) (TC 2))\n      )\n    )\n  )\n)\n)\n')
    flat, _ = S.read_nested_saif(saif)
    assert flat["u_d.g_line.line[3]"] == (90, 10, 0, 2) and flat["st[0]"] == (70, 30, 0, 4)
    out = tmp_path / "m.saif"
    st = S.map_rtl_saif_to_netlist(saif, net, out)
    assert st["flops"] == 3 and st["flops_matched"] == 2 and st["ports_matched"] == 2
    text = out.read_text()
    # QN is the inverted register: T0 and T1 swap, the toggle count is the register's
    assert "(QN (T0 10) (T1 90) (TX 0) (TC 2))" in text
    assert "(INSTANCE u_d.genblk1.g_line.line\\[3\\]$_DFF_P_" in text


@pytest.mark.skipif(shutil.which("g++") is None, reason="needs g++")
def test_vcd2saif_ignores_zero_delay_glitches_and_dump_gaps(tmp_path):
    exe = S.build_vcd2saif(tmp_path)
    vcd = tmp_path / "g.vcd"
    vcd.write_text("$timescale 1ps $end\n$scope module t $end\n$var wire 1 ! a $end\n$upscope $end\n"
                   "$enddefinitions $end\n#0\n0!\n#100\n1!\n0!\n1!\n#200\n0!\n$dumpoff\nx!\n$end\n"
                   "#500\n$dumpon\n1!\n$end\n#600\n")
    out = tmp_path / "g.saif"
    subprocess.run([str(exe), str(vcd), str(out), "t", "auto"], check=True, capture_output=True)
    text = out.read_text()
    # 0 -> (1,0,1 at one timestamp = 1) -> 0 -> [gap] -> 1: three toggles, the gap is not observed
    assert "(a (T0 100) (T1 200) (TX 0) (TC 3))" in text
    assert "(DURATION 300)" in text
