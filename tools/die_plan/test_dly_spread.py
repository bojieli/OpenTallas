"""dly_spread.tcl (FABLE-GENBUG G8, brief 4.3 DLY-SPREAD 11-15): zero-logic register pipes without a plan site are spread on the
route driver -> load centroid; stage identity is connectivity (D of stage k = Q of stage k-1), the last stage is named <inst>.q (G1
naming); plan-sited (FIRM) stages are anchors; a chain inside the reach is left alone; the hook fails closed.
Needs docker + openroad/orfs:asap7lock (skipped otherwise).   python3 -m pytest -q tools/die_plan/test_dly_spread.py"""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
FF, BUF = "DFFHQNx1_ASAP7_75t_R", "BUFx2_ASAP7_75t_R"


def _netlist():
    w, body = ["a", "Bb"], []

    def pipe(inst, n, d, tag):
        """n stages inst.g_reg.r[0..n-2], last inst.q (Yosys naming); returns the output net"""
        for k in range(n):
            o = f"{tag}_o{k}"
            w.append(o)
            nm = "q" if k == n - 1 else f"g_reg.r[{k}]"
            body.append(f"  {FF} \\{inst}.{nm}$_DFF_P_  (.CLK(clk), .D({d}), .QN({o}));")
            d = o
        return d
    body.append(f"  {FF} src (.CLK(clk), .D(1'b0), .QN(a));")
    # A: 9 stages, source far from the load, all stages clumped at the load end (col_h9_r1 u_d10_6_Y)
    o = pipe("u_bound.u_d10_6_Y", 9, "a", "A")
    body.append(f"  {FF} ldA (.CLK(clk), .D({o}), .QN());")
    # B: 5 stages behind a BUF; stage r[2] is sited by the plan (FIRM): the runs on both sides spread between anchors
    body.append(f"  {BUF} bufB (.A(a), .Y(Bb));")
    o = pipe("u_bound.u_d3_x", 5, "Bb", "B")
    body.append(f"  {FF} ldB (.CLK(clk), .D({o}), .QN());")
    # C: 3 stages, every hop inside the reach: untouched
    o = pipe("u_bound.u_d4_short", 3, "a", "C")
    body.append(f"  {FF} ldC (.CLK(clk), .D({o}), .QN());")
    # D: r[0] feeds r[1] AND a second flop: r[0] ends its chain (a tail with 2 loads), r[1] starts a new one
    o = pipe("u_bound.u_d5_fan", 2, "a", "D")
    body.append(f"  {FF} ldD0 (.CLK(clk), .D(D_o0), .QN());")
    body.append(f"  {FF} ldD1 (.CLK(clk), .D({o}), .QN());")
    v = ["module t(input wire clk, output wire y);"] + [f"  wire {x};" for x in w] + body + ["  assign y = 1'b0;\nendmodule\n"]
    return "\n".join(v)


TCL = r"""
set P /OpenROAD-flow-scripts/flow/platforms/asap7/lef
read_lef $P/asap7_tech_1x_201209.lef
read_lef $P/asap7sc7p5t_28_R_1x_220121a.lef
read_verilog /w/t.v
link_design t
initialize_floorplan -die_area "0 0 3000 600" -core_area "5 5 2995 595" -site asap7sc7p5t
set blk [ord::get_db_block]
set u [[ord::get_db_tech] getDbUnitsPerMicron]
proc put {i x y st} { global u; $i setLocation [expr {int($x*$u)}] [expr {int($y*$u)}]; $i setPlacementStatus $st }
foreach i [$blk getInsts] {
  set n [string map {\\ {}} [$i getName]]
  if {$n eq "src"} { put $i 100 300 FIRM
  } elseif {$n eq "ldA"} { put $i 2500 300 FIRM
  } elseif {$n eq "ldB"} { put $i 2400 100 FIRM
  } elseif {$n eq "ldC"} { put $i 400 300 FIRM
  } elseif {[string match ldD* $n]} { put $i 2000 500 FIRM
  } elseif {$n eq "u_bound.u_d3_x.g_reg.r\[2\]\$_DFF_P_"} { put $i 1000 100 FIRM
  } elseif {[string match u_bound.u_d4_short* $n]} { put $i 250 300 PLACED
  } else { put $i 2450 300 PLACED }
}
proc stage_x {pat} { global blk u; set r {}; foreach i [$blk getInsts] { set n [string map {\\ {}} [$i getName]]; if {[string match $pat $n]} { lappend r [list $n [expr {[[$i getBBox] xMin] / double($u)}]] } }; return [lsort -index 0 $r] }
proc worst {names src} {
  global blk u
  set prev $src; set w 0
  foreach n $names { set b [[$blk findInst $n] getBBox]; set x [expr {[$b xMin]/double($u)}]; set y [expr {[$b yMin]/double($u)}]
    set w [expr {max($w, abs($x-[lindex $prev 0])+abs($y-[lindex $prev 1]))}]; set prev [list $x $y] }
  return [list $w $prev]
}
set A {}; foreach k {0 1 2 3 4 5 6 7} { lappend A "u_bound.u_d10_6_Y.g_reg.r\\\[$k\\\]\$_DFF_P_" }; lappend A "u_bound.u_d10_6_Y.q\$_DFF_P_"
puts "BEFORE_A [worst $A {100 300}]"
set ::env(OT_DLY_SPREAD) warn
source /w/dly_spread.tcl
puts "AFTER_A [worst $A {100 300}]"
foreach i [$blk getInsts] { set n [string map {\\ {}} [$i getName]]; set b [$i getBBox]
  if {[string match "u_bound.u_d*" $n] || $n eq "bufB"} { puts "POS $n [expr {[$b xMin]/double($u)}] [expr {[$b yMin]/double($u)}]" } }
# fail closed: a 3-stage chain whose load is out of any ideal
"""

TCL_FAIL = r"""
set P /OpenROAD-flow-scripts/flow/platforms/asap7/lef
read_lef $P/asap7_tech_1x_201209.lef
read_lef $P/asap7sc7p5t_28_R_1x_220121a.lef
read_verilog /w/t.v
link_design t
initialize_floorplan -die_area "0 0 3000 600" -core_area "5 5 2995 595" -site asap7sc7p5t
set blk [ord::get_db_block]
set u [[ord::get_db_tech] getDbUnitsPerMicron]
# pipe A has its stage r[2] sited by the plan at the load end (FIRM, an anchor) and the 2 stages before it cannot make equal hops
# over the whole pipe: its worst hop stays over 1.5 x ideal -> FAIL.  A chain whose stages are ALL sited never fails.
foreach i [$blk getInsts] {
  set n [string map {\\ {}} [$i getName]]
  set st PLACED
  if {$n eq "src" || [string match ld* $n] || $n eq "u_bound.u_d10_6_Y.g_reg.r\[2\]\$_DFF_P_"} { set st FIRM }
  if {[string match ld* $n]} { set x 2500 } elseif {$n eq "src"} { set x 100 } else { set x 2450 }
  $i setLocation [expr {int($x * $u)}] [expr {int(300 * $u)}]; $i setPlacementStatus $st
}
if {[catch {source /w/dly_spread.tcl} e]} { puts "CAUGHT $e" }
"""


def _run(tcl, d):
    (Path(d) / "t.v").write_text(_netlist())
    (Path(d) / "t.tcl").write_text(tcl)
    shutil.copy(HERE / "dly_spread.tcl", d)
    cmd = "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /w/t.tcl; chmod -R a+rwX /w"
    r = subprocess.run(["docker", "run", "--rm", "--memory=4g", "--memory-swap=4g", "-v", f"{d}:/w",
                        "openroad/orfs:asap7lock", "bash", "-lc", cmd], capture_output=True, text=True, timeout=600)
    if r.returncode and "Unable to find image" in r.stderr:
        pytest.skip("image missing")
    return r.stdout


def test_dly_spread_moves_clumped_pipes_only():
    if not shutil.which("docker"):
        pytest.skip("no docker")
    with tempfile.TemporaryDirectory() as d:
        out = _run(TCL, d)
        b = re.search(r"BEFORE_A (\S+)", out)
        a = re.search(r"AFTER_A (\S+)", out)
        assert b and a, out[-3000:]
        assert float(b.group(1)) > 2000 and float(a.group(1)) <= 2400 / 10 * 1.5, (b.group(1), a.group(1))   # ideal 240 um
        pos = {m.group(1): (float(m.group(2)), float(m.group(3))) for m in re.finditer(r"POS (\S+) ([0-9.]+) ([0-9.]+)", out)}
        # A: stage identity by connectivity, evenly spaced between src (100) and load (2500): 9 stages -> 240 um apart
        xs = [pos[f"u_bound.u_d10_6_Y.g_reg.r[{k}]$_DFF_P_"][0] for k in range(8)] + [pos["u_bound.u_d10_6_Y.q$_DFF_P_"][0]]
        assert all(abs(xs[k] - (100 + 240 * (k + 1))) <= 30 for k in range(9)), xs
        # B: the FIRM stage r[2] did not move; r[0], r[1] sit between the BUF's driver and r[2]; r[3], r[4] between r[2] and the load
        assert pos["u_bound.u_d3_x.g_reg.r[2]$_DFF_P_"] == (1000.0, 100.0)
        x = [pos[f"u_bound.u_d3_x.g_reg.r[{k}]$_DFF_P_"][0] for k in range(4)] + [pos["u_bound.u_d3_x.q$_DFF_P_"][0]]
        assert 100 < x[0] < x[1] < 1000 < x[3] < x[4] < 2400, x
        assert 100 < pos["bufB"][0] < 1000                                        # the repeater of hop 0 goes with the chain
        # C: inside the reach: not touched (all three stages at x = 250)
        assert {pos[k][0] for k in pos if k.startswith("u_bound.u_d4_short")} == {250.0}
        # D: r[0] has two loads, so it is a one-stage chain whose tail is the load centroid; r[1] a separate chain
        assert re.search(r"OT_DLY_SPREAD chains \d+ stages \d+ moved \d+ skipped \d+ max_hop \d+ -> \d+ um \(chains over 405 um: \d+ -> \d+\)", out), out[-2000:]
        assert "fail 0" in out


def test_dly_spread_fails_closed():
    if not shutil.which("docker"):
        pytest.skip("no docker")
    with tempfile.TemporaryDirectory() as d:
        out = _run(TCL_FAIL, d)
        assert re.search(r"OT_DLY_SPREAD FAIL: \d+ chain", out) and "CAUGHT OT_DLY_SPREAD" in out, out[-2000:]


def test_dly_spread_is_wired_and_generic():
    tcl = (HERE / "dly_spread.tcl").read_text()
    assert "ot_face_flops.txt" in tcl and "OT_DLY_SPREAD_RE" in tcl
    assert "u_d" not in tcl.replace("u_d<N>", "").split("# Log:")[1]         # no die / type / instance name in the logic


def test_dly_spread_budget_key_installs_the_hook():
    import json
    import gen_phys
    import schema
    g = (HERE / "gen_phys.py").read_text()
    assert "dly_spread_mode(P.budgets, tn)" in g and "dly_spread.tcl" in g
    assert gen_phys.DLY_SPREAD_HOOK == "source /work/dly_spread.tcl"
    sch = schema.SCHEMA["properties"]["budgets"]["properties"]["r_dly_spread"]
    on_disk = json.loads((HERE / "die_plan.schema.json").read_text())
    assert on_disk["properties"]["budgets"]["properties"]["r_dly_spread"] == sch
    assert {"type": "boolean"} in sch["anyOf"] and any(x.get("type") == "array" for x in sch["anyOf"])
    # true: every type, gate; list of type base names: listed types only, warn; else off
    m = gen_phys.dly_spread_mode
    assert m({"r_dly_spread": True}, "any__t1") == "gate"
    assert m({"r_dly_spread": ["dsdv_slice_c1x_C"]}, "dsdv_slice_c1x_C__t1") == "warn"
    assert m({"r_dly_spread": ["dsdv_slice_c1x_C"]}, "cbf_q01") is None
    assert m({"r_dly_spread": []}, "cbf_q01") is None and m({}, "cbf_q01") is None and m({"r_dly_spread": False}, "x") is None
    assert "export OT_DLY_SPREAD = warn" in (HERE / "gen_phys.py").read_text()


def test_dly_spread_station_form_groups_stages():
    """XTAP-A (FABLE-FIX-KV-PV 11-20): OT_DLY_SPREAD_STATION_UM groups the stages of a run on ceil(L/S)-1 stations, so
    back-to-back stages sit together (one clock tap) and only the station hops (<= S of route) carry wire."""
    if not shutil.which("docker"):
        pytest.skip("no docker")
    with tempfile.TemporaryDirectory() as d:
        out = _run(TCL.replace("set ::env(OT_DLY_SPREAD) warn", "set ::env(OT_DLY_SPREAD) warn\nset ::env(OT_DLY_SPREAD_STATION_UM) 800"), d)
        pos = {m.group(1): (float(m.group(2)), float(m.group(3))) for m in re.finditer(r"POS (\S+) ([0-9.]+) ([0-9.]+)", out)}
        # A: route 2400 um, S 800 -> 2 stations at 900 and 1700; 9 stages -> r[0..4] on the first, r[5..7] + q on the second
        xs = [pos[f"u_bound.u_d10_6_Y.g_reg.r[{k}]$_DFF_P_"][0] for k in range(8)] + [pos["u_bound.u_d10_6_Y.q$_DFF_P_"][0]]
        assert all(abs(x - 900) <= 30 for x in xs[:5]) and all(abs(x - 1700) <= 30 for x in xs[5:]), xs
        a = re.search(r"AFTER_A (\S+)", out)
        assert a and float(a.group(1)) <= 830, out[-2000:]
        # B: FIRM r[2] stays an anchor; C untouched; no ratio failure (the ideal hop is the station hop)
        assert pos["u_bound.u_d3_x.g_reg.r[2]$_DFF_P_"] == (1000.0, 100.0)
        assert {pos[k][0] for k in pos if k.startswith("u_bound.u_d4_short")} == {250.0}
        assert "fail 0" in out, out[-2000:]


def test_dly_spread_station_key():
    import gen_phys
    import schema
    m = gen_phys.dly_spread_station_um
    assert m({}, "kv3_pv_v8") is None and m({"r_dly_spread_station_um": {"kv3_pv": 405}}, "kv3_hub_C") is None
    assert m({"r_dly_spread_station_um": {"kv3_pv": 405, "kv3_pv_v8": 300}}, "kv3_pv_v8__x") == 300.0
    assert "OT_DLY_SPREAD_STATION_UM" in (HERE / "gen_phys.py").read_text()
    assert schema.SCHEMA["properties"]["budgets"]["properties"]["r_dly_spread_station_um"]["type"] == "object"


def _netlist_seg():
    """XTAP-C: one bit of a split pad trunk: 3 segments of 3 stages (r[0], r[1], q) with a hop lockup latch between segments"""
    w, body = ["a"], [f"  {FF} src (.CLK(clk), .D(1'b0), .QN(a));"]
    d = "a"
    for j in range(3):
        for k, nm in enumerate(("r[0]", "r[1]", "q")):
            o = f"E_{j}_{k}"
            w.append(o)
            body.append(f"  {FF} \\u_bound.u_pd9_x_t_5_sg{j}.{nm}$_DFF_P_  (.CLK(clk), .D({d}), .QN({o}));")
            d = o
        if j < 2:
            o = f"E_l{j}"
            w.append(o)
            body.append(f"  DLLx1_ASAP7_75t_R \\u_bound.u_fl_pd9_x_t_5_sg{j + 1}.q$_DLATCH_N_  (.CLK(clk), .D({d}), .Q({o}));")
            d = o
    body.append(f"  {FF} ldE (.CLK(clk), .D({d}), .QN());")
    return "\n".join(["module t(input wire clk, output wire y);"] + [f"  wire {x};" for x in w] + body + ["  assign y = 1'b0;\nendmodule\n"])


TCL_SEG = r"""
set P /OpenROAD-flow-scripts/flow/platforms/asap7/lef
read_lef $P/asap7_tech_1x_201209.lef
read_lef $P/asap7sc7p5t_28_R_1x_220121a.lef
read_verilog /w/t.v
link_design t
initialize_floorplan -die_area "0 0 3000 600" -core_area "5 5 2995 595" -site asap7sc7p5t
set blk [ord::get_db_block]
set u [[ord::get_db_tech] getDbUnitsPerMicron]
foreach i [$blk getInsts] {
  set n [string map {\\ {}} [$i getName]]
  set st PLACED; set x 2450
  if {$n eq "src"} { set x 100; set st FIRM } elseif {$n eq "ldE"} { set x 2500; set st FIRM } elseif {$n eq "@ANCHOR@"} { set x 2400; set st FIRM }
  $i setLocation [expr {int($x * $u)}] [expr {int(300 * $u)}]; $i setPlacementStatus $st
}
set ::env(OT_DLY_SPREAD) warn
set ::env(OT_DLY_SPREAD_SEG) 1
set ::env(OT_DLY_SPREAD_STATION_UM) 405
source /w/dly_spread.tcl
foreach i [$blk getInsts] { set n [string map {\\ {}} [$i getName]]; set b [$i getBBox]; puts "POS $n [expr {[$b xMin]/double($u)}] [expr {[$b yMin]/double($u)}]" }
"""


def _run_seg(tcl, d):
    (Path(d) / "t.v").write_text(_netlist_seg())
    (Path(d) / "t.tcl").write_text(tcl)
    shutil.copy(HERE / "dly_spread.tcl", d)
    cmd = "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /w/t.tcl; chmod -R a+rwX /w"
    r = subprocess.run(["docker", "run", "--rm", "--memory=4g", "--memory-swap=4g", "-v", f"{d}:/w",
                        "openroad/orfs:asap7lock", "bash", "-lc", cmd], capture_output=True, text=True, timeout=600)
    if r.returncode and "Unable to find image" in r.stderr:
        pytest.skip("image missing")
    return r.stdout


def test_dly_spread_segment_form_latch_groups():
    """XTAP-C (FABLE-FIX-KV-PV 11-20): OT_DLY_SPREAD_SEG=1: the stages between two hop lockup latches are one station, the
    latch sits mid-hop; a group that reaches a FIRM stage with no latch between sits at that stage."""
    if not shutil.which("docker"):
        pytest.skip("no docker")
    with tempfile.TemporaryDirectory() as d:
        out = _run_seg(TCL_SEG, d)
        pos = {m.group(1): float(m.group(2)) for m in re.finditer(r"POS (\S+) ([0-9.]+) ([0-9.]+)", out)}
        assert pos, out[-3000:]
        seg = lambda j: [pos[f"u_bound.u_pd9_x_t_5_sg{j}.{nm}$_DFF_P_"] for nm in ("r[0]", "r[1]", "q")]  # noqa: E731
        # no anchor stage: 3 groups at 1/4, 2/4, 3/4 of 100 -> 2500
        for j, x in enumerate((700, 1300, 1900)):
            assert all(abs(v - x) <= 30 for v in seg(j)), (j, seg(j), out[-1500:])
            if j:
                assert abs(pos[f"u_bound.u_fl_pd9_x_t_5_sg{j}.q$_DLATCH_N_"] - (x - 300)) <= 30   # mid-hop
        assert "fail 0" in out, out[-2000:]
    with tempfile.TemporaryDirectory() as d:
        out = _run_seg(TCL_SEG.replace("@ANCHOR@", "u_bound.u_pd9_x_t_5_sg2.q\\$_DFF_P_"), d)
        pos = {m.group(1): float(m.group(2)) for m in re.finditer(r"POS (\S+) ([0-9.]+) ([0-9.]+)", out)}
        seg = lambda j: [pos[f"u_bound.u_pd9_x_t_5_sg{j}.{nm}$_DFF_P_"] for nm in ("r[0]", "r[1]", "q")]  # noqa: E731
        # the last stage is FIRM at 2400: its group sits there, the two free groups at 1/3 and 2/3 of 100 -> 2400
        assert all(abs(v - 2400) <= 30 for v in seg(2)), (seg(2), out[-1500:])
        assert all(abs(v - 867) <= 30 for v in seg(0)) and all(abs(v - 1633) <= 30 for v in seg(1)), (seg(0), seg(1))
