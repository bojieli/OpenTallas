"""relay_mid.tcl (S81-P8 10-23): soft relay chains sit on the straight line between their fixed source and fixed sink.
S81 g3k3 review 10-24: a chain whose tail feeds the face flop through the seam writer's chunk clear (q = rq ? i : 0, an
AND2 per bit) must still count the face flop as its fixed sink (it was left to GPL: 4 stages bunched at the source).
Needs docker + openroad/orfs:asap7lock (skipped otherwise).   python3 -m pytest -q tools/die_plan/test_relay_mid.py"""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
FF, AND = "DFFHQNx1_ASAP7_75t_R", "AND2x2_ASAP7_75t_R"
W = 4


def _netlist(gate):
    """src (FIRM, 100,100) -> relay u_y_a -> relay u_y_b -> [AND2 with rq | direct] -> sink (FIRM, 1300,1000)."""
    v = ["module t(input wire clk, input wire a, output wire y);", "  wire rq;"]
    v += [f"  wire s{k}, a{k}, b{k}, g{k};" for k in range(W)]
    v.append(f"  {FF} rqf (.CLK(clk), .D(a), .QN(rq));")
    for k in range(W):
        v.append(f"  {FF} src{k} (.CLK(clk), .D(a), .QN(s{k}));")
        v.append(f"  {FF} \\u_y_a.r[{k}]  (.CLK(clk), .D(s{k}), .QN(a{k}));")
        v.append(f"  {FF} \\u_y_b.r[{k}]  (.CLK(clk), .D(a{k}), .QN(b{k}));")
        if gate:
            v.append(f"  {AND} gt{k} (.A(rq), .B(b{k}), .Y(g{k}));")
        v.append(f"  {FF} snk{k} (.CLK(clk), .D({'g' if gate else 'b'}{k}), .QN());")
    v.append("  assign y = rq;\nendmodule\n")
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
foreach i [$blk getInsts] {
  set n [$i getName]
  if {[string match src* $n]} { $i setLocation [expr {100 * $u}] [expr {100 * $u}]; $i setPlacementStatus FIRM
  } elseif {[string match snk* $n]} { $i setLocation [expr {1300 * $u}] [expr {1000 * $u}]; $i setPlacementStatus FIRM
  } else { $i setLocation [expr {100 * $u}] [expr {110 * $u}]; $i setPlacementStatus PLACED }
}
set ::env(RESULTS_DIR) /w
set ::env(OT_RELAY_MID_RE) {^(u_y_[a-z]+)[.]}
source /w/relay_mid.tcl
foreach i [$blk getInsts] {
  set n [string map {\\ {}} [$i getName]]
  if {[regexp {^u_y_([ab])} $n -> g]} {
    set b [$i getBBox]
    puts "CHK $g [expr {[$b xMin] / double($u)}] [expr {[$b yMin] / double($u)}] [$i getPlacementStatus]"
  }
}
"""


@pytest.mark.parametrize("gate", [False, True])
def test_relay_chain_on_line(gate):
    if not shutil.which("docker"):
        pytest.skip("no docker")
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "t.v").write_text(_netlist(gate))
        (Path(d) / "t.tcl").write_text(TCL)
        shutil.copy(HERE / "relay_mid.tcl", d)
        cmd = "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /w/t.tcl; chmod -R a+rwX /w"
        r = subprocess.run(["docker", "run", "--rm", "--memory=4g", "--memory-swap=4g", "-v", f"{d}:/w",
                            "openroad/orfs:asap7lock", "bash", "-lc", cmd], capture_output=True, text=True, timeout=600)
        if r.returncode and "Unable to find image" in r.stderr:
            pytest.skip("image missing")
        out = r.stdout
        assert "OT_RELAY_MID placed 8 relay flops of 2 stations (2 relay groups)" in out, out[-3000:]
        pos = {}
        for g, x, y, st in re.findall(r"CHK ([ab]) ([0-9.]+) ([0-9.]+) (\w+)", out):
            assert st == "FIRM"
            pos.setdefault(g, []).append((float(x), float(y)))
        for g, j in (("a", 1), ("b", 2)):                 # stage j of 2 at L*j/3 on the src -> sink line
            ex, ey = 100 + 1200 * j / 3, 100 + 900 * j / 3
            assert all(abs(x - ex) + abs(y - ey) < 40 for x, y in pos[g]), (g, pos[g])
