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
    # E (DLY-REPAIR-1): src -> r[0] -> bufE -> r[1] (FIRM anchor) -> r[2] -> q -> ldE: the repeater of the hop that ENDS on the
    # anchor must sit between r[0] and r[1] (the next run's start once overwrote fr[anchor] = 0.0 and sent it backwards)
    w.extend(["E_o0", "E_b", "E_o1", "E_o2", "E_o3"])
    body.append(f"  {FF} \\u_bound.u_d6_anc.g_reg.r[0]$_DFF_P_  (.CLK(clk), .D(a), .QN(E_o0));")
    body.append(f"  {BUF} bufE (.A(E_o0), .Y(E_b));")
    body.append(f"  {FF} \\u_bound.u_d6_anc.g_reg.r[1]$_DFF_P_  (.CLK(clk), .D(E_b), .QN(E_o1));")
    body.append(f"  {FF} \\u_bound.u_d6_anc.g_reg.r[2]$_DFF_P_  (.CLK(clk), .D(E_o1), .QN(E_o2));")
    body.append(f"  {FF} \\u_bound.u_d6_anc.q$_DFF_P_  (.CLK(clk), .D(E_o2), .QN(E_o3));")
    body.append(f"  {FF} ldE (.CLK(clk), .D(E_o3), .QN());")
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
  } elseif {$n eq "u_bound.u_d6_anc.g_reg.r\[1\]\$_DFF_P_"} { put $i 1200 500 FIRM
  } elseif {$n eq "ldE"} { put $i 2500 500 FIRM
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
  if {[string match "u_bound.u_d*" $n] || $n eq "bufB" || $n eq "bufE"} { puts "POS $n [expr {[$b xMin]/double($u)}] [expr {[$b yMin]/double($u)}]" } }
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


def test_dly_spread_keeps_unroutable_station_chains():
    """No clear path around hard macros keeps the GPL positions and records NOROUTE."""
    if not shutil.which("docker"):
        pytest.skip("no docker")
    source = r"""
set ::env(OT_DLY_SPREAD_STATION_UM) 800
set hook [open /w/dly_spread.tcl r]
set script [read $hook]
close $hook
set blocked_route "proc ds_route {a b} { return {} }"
eval [string map [list "\nds_main\n" "\n$blocked_route\nds_main\n"] $script]
"""
    with tempfile.TemporaryDirectory() as d:
        out = _run(TCL.replace("source /w/dly_spread.tcl", source), d)
    assert re.search(r"OT_DLY_SPREAD NOROUTE [1-9]\d* chains", out), out[-2000:]
    before = re.search(r"BEFORE_A (.+)", out)
    after = re.search(r"AFTER_A (.+)", out)
    assert before and after and before.group(1) == after.group(1), out[-2000:]


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


def _netlist_rep():
    """REPEATER ANCHOR: a 2-stage pad tail whose hops are inside the reach, its D fed by the trunk Q through an INV + BUF that GPL
    left 1,800 um away (kv3_pv v8j); plus a 3-stage chain with 200/350/350/300 um hops (inside 405, over a 300 um station reach)."""
    w = ["a", "g_i", "g_b", "h"]
    body = [f"  {FF} trunk (.CLK(clk), .D(1'b0), .QN(a));",
            "  INVx1_ASAP7_75t_R inv_far (.A(a), .Y(g_i));",
            f"  {BUF} buf_far (.A(g_i), .Y(g_b));"]
    d = "g_b"
    for k, nm in enumerate(("r[0]", "q")):
        o = f"F_{k}"
        w.append(o)
        body.append(f"  {FF} \\u_bound.u_pd2_tail.{nm}$_DFF_P_  (.CLK(clk), .D({d}), .QN({o}));")
        d = o
    body.append(f"  {FF} ldF (.CLK(clk), .D({d}), .QN());")
    body.append(f"  {FF} src3 (.CLK(clk), .D(1'b0), .QN(h));")
    d = "h"
    for k, nm in enumerate(("r[0]", "r[1]", "q")):
        o = f"G_{k}"
        w.append(o)
        body.append(f"  {FF} \\u_bound.u_pd3_mid.{nm}$_DFF_P_  (.CLK(clk), .D({d}), .QN({o}));")
        d = o
    body.append(f"  {FF} ldG (.CLK(clk), .D({d}), .QN());")
    return "\n".join(["module t(input wire clk, output wire y);"] + [f"  wire {x};" for x in w] + body + ["  assign y = 1'b0;\nendmodule\n"])


TCL_REP = r"""
set P /OpenROAD-flow-scripts/flow/platforms/asap7/lef
read_lef $P/asap7_tech_1x_201209.lef
read_lef $P/asap7sc7p5t_28_R_1x_220121a.lef
read_verilog /w/t.v
link_design t
initialize_floorplan -die_area "0 0 3000 600" -core_area "5 5 2995 595" -site asap7sc7p5t
set blk [ord::get_db_block]
set u [[ord::get_db_tech] getDbUnitsPerMicron]
set XY [dict create trunk {2000 300 FIRM} inv_far {200 500 PLACED} buf_far {220 500 PLACED} ldF {2300 300 FIRM} \
  {u_bound.u_pd2_tail.r[0]$_DFF_P_} {2100 300 PLACED} {u_bound.u_pd2_tail.q$_DFF_P_} {2200 300 PLACED} \
  src3 {100 100 FIRM} {u_bound.u_pd3_mid.r[0]$_DFF_P_} {300 100 PLACED} {u_bound.u_pd3_mid.r[1]$_DFF_P_} {650 100 PLACED} \
  {u_bound.u_pd3_mid.q$_DFF_P_} {1000 100 PLACED} ldG {1300 100 FIRM}]
foreach i [$blk getInsts] {
  set n [string map {\\ {}} [$i getName]]
  lassign [dict get $XY $n] x y st
  $i setLocation [expr {int($x * $u)}] [expr {int($y * $u)}]; $i setPlacementStatus $st
}
set ::env(OT_DLY_SPREAD) warn
@STATION@
source /w/dly_spread.tcl
foreach i [$blk getInsts] { set n [string map {\\ {}} [$i getName]]; set b [$i getBBox]; puts "POS $n [expr {[$b xMin]/double($u)}] [expr {[$b yMin]/double($u)}]" }
"""


def _run_rep(tcl, d):
    (Path(d) / "t.v").write_text(_netlist_rep())
    (Path(d) / "t.tcl").write_text(tcl)
    shutil.copy(HERE / "dly_spread.tcl", d)
    cmd = "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /w/t.tcl; chmod -R a+rwX /w"
    r = subprocess.run(["docker", "run", "--rm", "--memory=4g", "--memory-swap=4g", "-v", f"{d}:/w",
                        "openroad/orfs:asap7lock", "bash", "-lc", cmd], capture_output=True, text=True, timeout=600)
    if r.returncode and "Unable to find image" in r.stderr:
        pytest.skip("image missing")
    return r.stdout


def test_dly_spread_repeater_anchor_and_station_reach():
    """KV-PLAN-R1 11-20: (1) a far repeater of an in-reach hop moves onto its hop (trunk 2000 -> tail r[0] 2100), the stages stay;
    (2) without a station reach the 350 um chain is inside 405 and stays; with OT_DLY_SPREAD_STATION_UM 300 it is re-spread."""
    if not shutil.which("docker"):
        pytest.skip("no docker")
    with tempfile.TemporaryDirectory() as d:
        out = _run_rep(TCL_REP.replace("@STATION@", ""), d)
        pos = {m.group(1): (float(m.group(2)), float(m.group(3))) for m in re.finditer(r"POS (\S+) ([0-9.]+) ([0-9.]+)", out)}
        assert pos, out[-3000:]
        assert 1990 <= pos["inv_far"][0] <= 2110 and 1990 <= pos["buf_far"][0] <= 2110, (pos["inv_far"], pos["buf_far"])
        assert pos["inv_far"][0] <= pos["buf_far"][0]                          # driver side first
        assert pos["u_bound.u_pd2_tail.r[0]$_DFF_P_"] == (2100.0, 300.0) and pos["u_bound.u_pd2_tail.q$_DFF_P_"] == (2200.0, 300.0)
        assert re.search(r"OT_DLY_SPREAD REPFIX repeaters 2 ", out), out[-2000:]
        assert [pos[f"u_bound.u_pd3_mid.{n}$_DFF_P_"][0] for n in ("r[0]", "r[1]", "q")] == [300.0, 650.0, 1000.0]
        assert "chains over 405 um" in out and "fail 0" in out
    with tempfile.TemporaryDirectory() as d:
        out = _run_rep(TCL_REP.replace("@STATION@", "set ::env(OT_DLY_SPREAD_STATION_UM) 300"), d)
        pos = {m.group(1): (float(m.group(2)), float(m.group(3))) for m in re.finditer(r"POS (\S+) ([0-9.]+) ([0-9.]+)", out)}
        xs = [pos[f"u_bound.u_pd3_mid.{n}$_DFF_P_"][0] for n in ("r[0]", "r[1]", "q")]
        assert all(abs(x - e) <= 30 for x, e in zip(xs, (400, 700, 1000))), xs   # re-spread to 300 um hops under the station reach
        assert "chains over 300 um" in out and "fail 0" in out, out[-2000:]


def test_dly_repair_hop_into_anchor_keeps_its_repeater_between_stages():
    """DLY-REPAIR-1 (1), QC cbf_q01_s2: a repeater of the hop that ends on an anchor stage goes between that hop's stages."""
    if not shutil.which("docker"):
        pytest.skip("no docker")
    with tempfile.TemporaryDirectory() as d:
        out = _run(TCL, d)
        pos = {m.group(1): (float(m.group(2)), float(m.group(3))) for m in re.finditer(r"POS (\S+) ([0-9.]+) ([0-9.]+)", out)}
        r0 = pos["u_bound.u_d6_anc.g_reg.r[0]$_DFF_P_"]
        r1 = pos["u_bound.u_d6_anc.g_reg.r[1]$_DFF_P_"]
        b = pos["bufE"]
        assert r1 == (1200.0, 500.0), r1
        lo, hi = min(r0[0], r1[0]), max(r0[0], r1[0])
        assert lo - 30 <= b[0] <= hi + 30 and 100 < r0[0] < 1200, (r0, b, r1)
        # no liberty in this session: the repair step says so and the pass still finishes
        assert "OT_DLY_SPREAD_REPAIR skipped: no liberty" in out, out[-2000:]
        assert "OT_DLY_SPREAD NOROUTE 0" in out, out[-2000:]


def test_dly_repair_repairs_moved_nets_with_liberty():
    """DLY-REPAIR-1 (3): with liberty loaded, the nets of the moved cells get a repair_design (others dont_touch)."""
    if not shutil.which("docker"):
        pytest.skip("no docker")
    libs = "".join(f"read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_{g}_RVT_TT_nldm_{v}.lib{"" if g == "SEQ" else ".gz"}\n"
                   for g, v in (("AO", "211120"), ("INVBUF", "220122"), ("OA", "211120"), ("SIMPLE", "211120"), ("SEQ", "220123")))
    tcl = TCL.replace("read_verilog /w/t.v", libs + "read_verilog /w/t.v").replace(
        "set ::env(OT_DLY_SPREAD) warn", "set ::env(OT_DLY_SPREAD) warn\nsource /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl")
    with tempfile.TemporaryDirectory() as d:
        out = _run(tcl, d)
        m = re.search(r"OT_DLY_SPREAD_REPAIR repair_design .*on (\d+) nets of (\d+) moved cells", out)
        assert m and int(m.group(1)) > 0 and int(m.group(2)) > 0, out[-3000:]
        assert re.search(r"OT_DLY_SPREAD_REPAIR leaf instances \d+ -> \d+", out), out[-3000:]


def test_dly_repair_no_straight_fallback_and_switch():
    tcl = (HERE / "dly_spread.tcl").read_text()
    assert "set best [list $A $B]" not in tcl                       # DLY-REPAIR-1 (2): never a straight route through a core
    assert "if {$r eq {}} { return {} }" in tcl                      # a cached 'no route' stays 'no route'
    assert "OT_DLY_SPREAD_REPAIR" in tcl and "setDoNotTouch 0" in tcl


def _netlist_final():
    """F (OPUS-FIX-KV-PV-R4): src -> bin (plan-sited, FIRM) -> two loads, each the head of a 9-stage pipe to a far load: the bin is a
    one-stage chain whose tail = those heads; it is measured before the pipes are spread (heads still at the far end)"""
    w, body = ["a", "b"], []
    body.append(f"  {FF} \\u_bound.u_bin_x/q[0]$_DFF_P_  (.CLK(clk), .D(a), .QN(b));")
    body.append(f"  {FF} src (.CLK(clk), .D(1'b0), .QN(a));")
    for t in ("P", "Q"):
        d = "b"
        for k in range(9):
            o = f"{t}_o{k}"
            w.append(o)
            nm = "q" if k == 8 else f"g_reg.r[{k}]"
            body.append(f"  {FF} \\u_bound.u_pd_{t}.{nm}$_DFF_P_  (.CLK(clk), .D({d}), .QN({o}));")
            d = o
        body.append(f"  {FF} ld{t} (.CLK(clk), .D({d}), .QN());")
    v = ["module t(input wire clk, output wire y);"] + [f"  wire {x};" for x in w] + body + ["  assign y = 1'b0;\nendmodule\n"]
    return "\n".join(v)


TCL_FINAL = r"""
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
  } elseif {[string match "u_bound.u_bin_x*" $n]} { put $i 150 300 FIRM
  } elseif {[string match ld* $n]} { put $i 2500 300 FIRM
  } else { put $i 2450 300 PLACED }
}
set ::env(OT_DLY_SPREAD) warn
source /w/dly_spread.tcl
"""


def test_dly_spread_final_line_remeasures_on_final_sites():
    if not shutil.which("docker"):
        pytest.skip("no docker")
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "t.v").write_text(_netlist_final())
        (Path(d) / "t.tcl").write_text(TCL_FINAL)
        shutil.copy(HERE / "dly_spread.tcl", d)
        cmd = "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /w/t.tcl; chmod -R a+rwX /w"
        r = subprocess.run(["docker", "run", "--rm", "--memory=4g", "--memory-swap=4g", "-v", f"{d}:/w",
                            "openroad/orfs:asap7lock", "bash", "-lc", cmd], capture_output=True, text=True, timeout=600)
        if r.returncode and "Unable to find image" in r.stderr:
            pytest.skip("image missing")
        out = r.stdout
        m = re.search(r"OT_DLY_SPREAD chains \d+ stages \d+ moved \d+ skipped \d+ max_hop \d+ -> (\d+) um", out)
        f = re.search(r"OT_DLY_SPREAD FINAL max_hop (\d+) um on final sites \(chains over \d+ um: (\d+)\) worst (\S+) stages (\d+)", out)
        assert m and f, out[-3000:]
        # the in-pass number keeps the bin's stale hop (heads still at x 2450: ~2,300 um); on the final sites every hop is ~235 um
        assert int(m.group(1)) > 2000, m.group(0)
        assert int(f.group(1)) <= 300 and f.group(2) == "0", f.group(0)


def test_dly_spread_route_end_inside_macro_moves_out():
    """ROUTE-END-OUT (KV-PV-FANOUT 11-24): a route end inside a hard macro (a macro pin, or the load centroid of tail copies that
    ring a core group) moves to the nearest point of the macro's halo box, so the chain gets a route instead of NOROUTE;
    OT_DLY_SPREAD_END_OUT=0 keeps the old behaviour (no route)."""
    if not shutil.which("docker"):
        pytest.skip("no docker")
    checks = r"""
set ds_mac [list [list [expr {1000000 - $ds_halo}] [expr {100000 - $ds_halo}] [expr {1400000 + $ds_halo}] [expr {500000 + $ds_halo}]]]
set ds_xi {}; set ds_yi {}
foreach ds_m $ds_mac { lassign $ds_m a b c d; lappend ds_xi [list [expr {$a + $ds_halo}] [expr {$c - $ds_halo}]]; lappend ds_yi [list [expr {$b + $ds_halo}] [expr {$d - $ds_halo}]] }
set ds_xs [ds_lines [$ds_core xMin] [$ds_core xMax] $ds_xi]
set ds_ys [ds_lines [$ds_core yMin] [$ds_core yMax] $ds_yi]
set ds_rcache {}
puts "OUT_IN [ds_out {1100000 300000}]"
puts "OUT_FREE [ds_out {200000 300000}]"
puts "OUT_EDGE [ds_out {1001000 300000}]"
set r [ds_route {200000 300000} {1100000 300000}]
puts "ROUTE_N [llength $r] END [lindex $r end] OK [ds_pok $r]"
set ds_endout 0; set ds_rcache {}
puts "ROUTE_OFF [llength [ds_route {200000 300000} {1100000 300000}]]"
"""
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "t.v").write_text(_netlist())
        tcl = TCL.split("source /w/dly_spread.tcl")[0] + r"""
set hook [open /w/dly_spread.tcl r]
set script [read $hook]
close $hook
eval [string map [list "\nds_main\n" "\nsource /w/chk.tcl\n"] $script]
"""
        (Path(d) / "t.tcl").write_text(tcl)
        (Path(d) / "chk.tcl").write_text(checks)
        shutil.copy(HERE / "dly_spread.tcl", d)
        cmd = "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /w/t.tcl; chmod -R a+rwX /w"
        r = subprocess.run(["docker", "run", "--rm", "--memory=4g", "--memory-swap=4g", "-v", f"{d}:/w",
                            "openroad/orfs:asap7lock", "bash", "-lc", cmd], capture_output=True, text=True, timeout=600)
        if r.returncode and "Unable to find image" in r.stderr:
            pytest.skip("image missing")
        out = r.stdout
    halo = 9000
    assert f"OUT_IN {1000000 - halo} 300000" in out, out[-2000:]
    assert "OUT_FREE 200000 300000" in out and "OUT_EDGE 1001000 300000" in out, out[-2000:]
    m = re.search(r"ROUTE_N (\d+) END (\S+ \S+) OK (\d)", out)
    assert m and int(m.group(1)) >= 2 and m.group(2) == f"{1000000 - halo} 300000" and m.group(3) == "1", out[-2000:]
    assert "ROUTE_OFF 0" in out, out[-2000:]


def test_dly_spread_maze_fallback_routes_round_a_macro():
    """MAZE (KV-PV-FANOUT 11-24): with no street-line route (here: no street lines at all, a macro across the straight path)
    ds_route falls back to a grid path round the macro that ds_pok clears; OT_DLY_SPREAD_MAZE_UM=0 keeps {}."""
    if not shutil.which("docker"):
        pytest.skip("no docker")
    checks = r"""
set ds_mac [list [list [expr {1000000 - $ds_halo}] [expr {100000 - $ds_halo}] [expr {1400000 + $ds_halo}] [expr {500000 + $ds_halo}]]]
set ds_xs {}; set ds_ys {}; set ds_rcache {}; set ds_mz_built 0
set r [ds_route {200000 300000} {1600000 300000}]
puts "MAZE_N [llength $r] OK [ds_pok $r] LEN [ds_plen $r] FIRST [lindex $r 0] LAST [lindex $r end]"
set rect 1; for {set k 1} {$k < [llength $r]} {incr k} { lassign [lindex $r [expr {$k-1}]] a b; lassign [lindex $r $k] c d; if {$a != $c && $b != $d} { set rect 0 } }
puts "MAZE_RECT $rect"
set ds_mz_um 0; set ds_rcache {}
puts "MAZE_OFF [llength [ds_route {200000 300000} {1600000 300000}]]"
"""
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "t.v").write_text(_netlist())
        tcl = TCL.split("source /w/dly_spread.tcl")[0] + r"""
set hook [open /w/dly_spread.tcl r]
set script [read $hook]
close $hook
eval [string map [list "\nds_main\n" "\nsource /w/chk.tcl\n"] $script]
"""
        (Path(d) / "t.tcl").write_text(tcl)
        (Path(d) / "chk.tcl").write_text(checks)
        shutil.copy(HERE / "dly_spread.tcl", d)
        cmd = "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /w/t.tcl; chmod -R a+rwX /w"
        r = subprocess.run(["docker", "run", "--rm", "--memory=4g", "--memory-swap=4g", "-v", f"{d}:/w",
                            "openroad/orfs:asap7lock", "bash", "-lc", cmd], capture_output=True, text=True, timeout=600)
        if r.returncode and "Unable to find image" in r.stderr:
            pytest.skip("image missing")
        out = r.stdout
    m = re.search(r"MAZE_N (\d+) OK (\d) LEN (\S+) FIRST (\S+ \S+) LAST (\S+ \S+)", out)
    assert m and int(m.group(1)) >= 4 and m.group(2) == "1", out[-2000:]
    assert m.group(4) == "200000 300000" and m.group(5) == "1600000 300000", m.group(0)
    assert 1400000 <= float(m.group(3)) <= 1400000 + 2 * 230000, m.group(0)    # straight 1400 um + a detour of <= ~2 x 220 um
    assert "MAZE_RECT 1" in out and "MAZE_OFF 0" in out, out[-2000:]
