"""forest_recluster.tcl (S81-P9 10-23): leaves of a landing reset forest are re-clustered to identical branch flops by
location; every hop <= 750 um; the only netlist edit is a leaf D moved between same-parity branch nets.
Needs docker + openroad/orfs:asap7lock (skipped otherwise).   python3 -m pytest -q tools/die_plan/test_forest.py"""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
FF, INV = "DFFHQNx1_ASAP7_75t_R", "INVx1_ASAP7_75t_R"
NPRE, NBR, NLEAF = 3, 3, 80
CLUMPS = [(200, 200), (1300, 1000), (1300, 200)]


def _netlist():
    """src -> prefix chain -> 3 branches (QN -> INV, as Yosys maps a kept copy) -> 80 leaves (leaf l on branch l/32);
    leaf l's load sits in clump l % 3, so the RTL assignment spans the die."""
    f = "u_f"
    v = ["module t(input wire clk, input wire a, output wire y);"]
    w = ["src_q", "pre_last"] + [f"p{i}" for i in range(NPRE)] + [f"bq{b}" for b in range(NBR)] + \
        [f"bo{b}" for b in range(NBR)] + [f"lq{n}" for n in range(NLEAF)]
    v += [f"  wire {x};" for x in w]
    v.append(f"  {FF} src (.CLK(clk), .D(a), .QN(src_q));")
    d = "src_q"
    for i in range(NPRE):
        v.append(f"  {FF} \\{f}.g_prefix[{i}].u_ff/value_reg  (.CLK(clk), .D({d}), .QN(p{i}));")
        d = f"p{i}"
    for b in range(NBR):
        v.append(f"  {FF} \\{f}.g_branch[{b}].u_ff/value_reg  (.CLK(clk), .D({d}), .QN(bq{b}));")
        v.append(f"  {INV} \\{f}.g_branch[{b}].u_ff/inv  (.A(bq{b}), .Y(bo{b}));")
    for n in range(NLEAF):
        v.append(f"  {FF} \\{f}.g_leaf[{n}].u_ff/value_reg  (.CLK(clk), .D(bo{n // 32}), .QN(lq{n}));")
        v.append(f"  {FF} ld{n} (.CLK(clk), .D(lq{n}), .QN());")
    # reset pipelines: u_c.u_lpr_root (3 stages, src -> load 1.3 mm), u_c.u_frl_rst (1 stage, 1.3 mm: 2 x 650 um),
    # u_c.u_lpr_ft0 (1 stage, 1.85 mm: NEED 2)
    for c, n in (("lpr_root", 3), ("frl_rst", 1), ("lpr_ft0", 1)):
        d = "src_q"
        for k in range(n):
            v.append(f"  wire {c}{k};")
            v.append(f"  {FF} \\u_c.u_{c}.g_reg.r[{k}]$_DFF_P_  (.CLK(clk), .D({d}), .QN({c}{k}));")
            d = f"{c}{k}"
        v.append(f"  {FF} cl_{c} (.CLK(clk), .D({d}), .QN());")
    v.append("  assign y = lq0;\nendmodule\n")
    return "\n".join(v)


TCL = r"""
set P /OpenROAD-flow-scripts/flow/platforms/asap7/lef
read_lef $P/asap7_tech_1x_201209.lef
read_lef $P/asap7sc7p5t_28_R_1x_220121a.lef
read_verilog /w/t.v
link_design t
initialize_floorplan -die_area "0 0 1500 1200" -core_area "5 5 1495 1195" -site asap7sc7p5t
set blk [ord::get_db_block]
set u [[ord::get_db_tech] getDbUnitsPerMicron]
# GPL-like start: loads FIRM in their clumps, leaves next to them, prefix / branch flops at the die centre, src at (100, 600)
set clumps {{200 200} {1300 1000} {1300 200}}
foreach i [$blk getInsts] {
  set n [string map {\\ {}} [$i getName]]
  if {[regexp {^cl_} $n]} {
    $i setLocation [expr {1400 * $u}] [expr {($n eq "cl_lpr_ft0" ? 1150 : 600) * $u}]; $i setPlacementStatus FIRM
  } elseif {[regexp {^ld([0-9]+)$} $n -> k] || [regexp {g_leaf\[([0-9]+)\]} $n -> k]} {
    lassign [lindex $clumps [expr {$k % 3}]] x y
    $i setLocation [expr {int(($x + ($k % 7) * 9 + ([string match ld* $n] ? 0 : 20)) * $u)}] [expr {int(($y + ($k % 5) * 10.8) * $u)}]
    $i setPlacementStatus [expr {[string match ld* $n] ? "FIRM" : "PLACED"}]
  } elseif {$n eq "src" || [string match "u_c.*" $n]} {
    $i setLocation [expr {100 * $u}] [expr {600 * $u}]; $i setPlacementStatus PLACED
  } else {
    $i setLocation [expr {750 * $u}] [expr {600 * $u}]; $i setPlacementStatus PLACED
  }
}
set ::env(RESULTS_DIR) /w
source /w/forest_recluster.tcl
# checks: every leaf D -> a branch flop through ONE inverter (the original parity); positions
foreach i [$blk getInsts] {
  set n [string map {\\ {}} [$i getName]]
  if {![regexp {g_leaf\[([0-9]+)\]} $n -> k] || ![fr_is_ff $i]} continue
  lassign [fr_src [[fr_pin $i D] getNet]] s par
  set sn [string map {\\ {}} [$s getName]]
  puts "CHK leaf $k src $sn par $par d [expr {[fr_md [fr_ctr $s] [fr_ctr $i]] / double($u)}]"
}
foreach i [$blk getInsts] {
  set n [string map {\\ {}} [$i getName]]
  if {[regexp {g_(prefix|branch)\[([0-9]+)\]} $n -> kind k] && [fr_is_ff $i]} {
    lassign [fr_src [[fr_pin $i D] getNet]] s par
    set sn [string map {\\ {}} [$s getName]]
    puts "CHK $kind $k src $sn par $par d [expr {[fr_md [fr_ctr $s] [fr_ctr $i]] / double($u)}]"
  }
}
"""


def test_forest_recluster():
    if not shutil.which("docker"):
        pytest.skip("no docker")
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "t.v").write_text(_netlist())
        (Path(d) / "t.tcl").write_text(TCL)
        shutil.copy(HERE / "forest_recluster.tcl", d)
        cmd = "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /w/t.tcl; chmod -R a+rwX /w"
        r = subprocess.run(["docker", "run", "--rm", "--memory=4g", "--memory-swap=4g", "-v", f"{d}:/w",
                            "openroad/orfs:asap7lock", "bash", "-lc", cmd], capture_output=True, text=True, timeout=600)
        if r.returncode and "Unable to find image" in r.stderr:
            pytest.skip("image missing")
        out = r.stdout
        assert "OT_FOREST_RECLUSTER 1 forests (0 skipped, 0 over the hop limit)" in out, out[-3000:]
        chk = re.findall(r"CHK (\w+) (\d+) src (\S+) par (\d) d ([0-9.]+)", out)
        leaves = [c for c in chk if c[0] == "leaf"]
        assert len(leaves) == NLEAF
        per = {}
        for _, k, src, par, dist in leaves:
            assert re.fullmatch(r"u_f\.g_branch\[\d\]\.u_ff/value_reg", src), src     # still a branch flop
            assert par == "1"                                                          # same parity as the RTL
            assert float(dist) <= 750.0
            per[src] = per.get(src, 0) + 1
        assert max(per.values()) <= 32 and sum(per.values()) == NLEAF
        for kind, k, src, par, dist in chk:
            if kind == "branch":
                assert src == f"u_f.g_prefix[{NPRE - 1}].u_ff/value_reg" and float(dist) <= 750.0
            if kind == "prefix":
                assert float(dist) <= 750.0
        log = (Path(d) / "ot_forest_recluster.txt").read_text()
        moved = [ln for ln in log.splitlines() if ln and not ln.startswith("#")]
        assert len(moved) == NLEAF and sum(1 for ln in moved if ln.split("\t")[2] != ln.split("\t")[3]) > 0
        # before: the RTL assignment l -> branch[l/32] had a leaf > 1 mm from its branch
        m = re.search(r"OT_RESET_CHAIN u_c.u_lpr_root: 3 stages, 1 loads, max hop (\d+) -> (\d+) um\n", out)
        assert m and int(m.group(1)) > 1000 and int(m.group(2)) <= 750, out[-3000:]
        assert re.search(r"OT_RESET_CHAIN u_c.u_frl_rst: 1 stages, 1 loads, max hop \d+ -> \d+ um\n", out)   # 650 + 650
        assert re.search(r"OT_RESET_CHAIN u_c.u_lpr_ft0: 1 stages, 1 loads, max hop \d+ -> \d+ um NEED 2 stages", out)
        m = re.search(r"branch->leaf max (\d+) -> (\d+) um", out)
        assert int(m.group(1)) > 750 >= int(m.group(2)), m.group(0)
