"""relay_mid.tcl STAGGER (FAM-S81-COL-H9R0-R3 11-21, FABLE-PD-S81-1100 fix 3; opt-in OT_RELAY_MID_STAGGER=1): parallel chains
with the same ends (the four slices of one xo bus) no longer get the same station point.  Two one-stage chains u_y_a / u_y_b
from FIRM sources at (300, 600) to FIRM sinks at (1000, 600): by default both clusters sit at the midpoint (one on top of the
other); with STAGGER they move apart perpendicular to the leg, each hop within the cap.  gen_phys exports the env only when
the GEN env or the plan asks for it, so kits without the key are byte-identical.
Needs docker + openroad/orfs:asap7lock for the Tcl runs (skipped otherwise).   python3 -m pytest -q tools/die_plan/test_relay_mid_stagger.py"""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

import gen_phys

HERE = Path(__file__).resolve().parent
FF = "DFFHQNx1_ASAP7_75t_R"
W = 32


def _netlist():
    v = ["module t(input wire clk, input wire a);"]
    for g in "ab":
        v += [f"  wire {g}s{k}, {g}r{k};" for k in range(W)]
        for k in range(W):
            v.append(f"  {FF} {g}src{k} (.CLK(clk), .D(a), .QN({g}s{k}));")
            v.append(f"  {FF} \\u_y_{g}.r[{k}]  (.CLK(clk), .D({g}s{k}), .QN({g}r{k}));")
            v.append(f"  {FF} {g}snk{k} (.CLK(clk), .D({g}r{k}), .QN());")
    v.append("endmodule\n")
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
  if {[regexp {^[ab]src} $n]} { $i setLocation [expr {300 * $u}] [expr {600 * $u}]; $i setPlacementStatus FIRM
  } elseif {[regexp {^[ab]snk} $n]} { $i setLocation [expr {1000 * $u}] [expr {600 * $u}]; $i setPlacementStatus FIRM
  } else { $i setLocation [expr {100 * $u}] [expr {110 * $u}]; $i setPlacementStatus PLACED }
}
set ::env(RESULTS_DIR) /w
set ::env(OT_RELAY_MID_RE) {^(u_y_[a-z]+)[.]}
source /w/relay_mid.tcl
foreach i [$blk getInsts] {
  set n [string map {\\ {}} [$i getName]]
  if {[regexp {^u_y_([ab])} $n -> g]} {
    set b [$i getBBox]
    puts "CHK $g [expr {[$b xMin] / double($u)}] [expr {[$b yMin] / double($u)}]"
  }
}
"""


def _run(env):
    if not shutil.which("docker"):
        pytest.skip("no docker")
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "t.v").write_text(_netlist())
        (Path(d) / "t.tcl").write_text(TCL)
        shutil.copy(HERE / "relay_mid.tcl", d)
        envs = []
        for k, v in env.items():
            envs += ["-e", f"{k}={v}"]
        cmd = "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /w/t.tcl; chmod -R a+rwX /w"
        r = subprocess.run(["docker", "run", "--rm", "--memory=4g", "--memory-swap=4g", *envs, "-v", f"{d}:/w",
                            "openroad/orfs:asap7lock", "bash", "-lc", cmd], capture_output=True, text=True, timeout=600)
        if r.returncode and "Unable to find image" in r.stderr:
            pytest.skip("image missing")
        out = r.stdout
        assert f"OT_RELAY_MID placed {2 * W} relay flops of 2 stations" in out, out[-3000:]
        pos = {"a": [], "b": []}
        for g, x, y in re.findall(r"CHK ([ab]) ([0-9.]+) ([0-9.]+)", out):
            pos[g].append((float(x), float(y)))
        assert len(pos["a"]) == W and len(pos["b"]) == W
        return out, pos


def _box(p):
    xs = [x for x, _ in p]; ys = [y for _, y in p]
    return min(xs), min(ys), max(xs), max(ys)


def test_default_unchanged_clusters_share_the_point():
    out, pos = _run({})
    assert "OT_RELAY_MID_STAGGER" not in out
    a, b = _box(pos["a"]), _box(pos["b"])
    # same line point: the second cluster stacks right on top of the first (rm_stack), within a few rows
    assert abs((a[0] + a[2]) - (b[0] + b[2])) < 1.0
    assert min(abs(b[1] - a[3]), abs(a[1] - b[3])) < 1.0


def test_stagger_moves_parallel_chains_apart_within_the_cap():
    out, pos = _run({"OT_RELAY_MID_STAGGER": "1"})
    assert "OT_RELAY_MID_STAGGER sets 1 chains moved 2 (halved 0) kept 0" in out, out[-2000:]
    a, b = _box(pos["a"]), _box(pos["b"])
    gap = max(b[1] - a[3], a[1] - b[3])
    assert gap >= 15.0, (a, b)                  # at least the 20-um gap, less the cluster rows of the stack offset
    for p in pos["a"] + pos["b"]:
        assert abs(p[0] - 300) + abs(p[1] - 600) <= 405 + 40 and abs(p[0] - 1000) + abs(p[1] - 600) <= 405 + 40


def test_stagger_opt_in(monkeypatch):
    monkeypatch.delenv("OT_RELAY_MID_STAGGER", raising=False)
    assert not gen_phys._relay_mid_stagger({}, "col_h9_r0_p2__t1__cl0045af7b__pva2793873")
    assert gen_phys._relay_mid_stagger({"relay_mid_stagger": True}, "x__t1")
    assert gen_phys._relay_mid_stagger({"relay_mid_stagger_types": ["col_h9_r0_p2"]}, "col_h9_r0_p2__t1__cl0045af7b__pva2793873")
    assert not gen_phys._relay_mid_stagger({"relay_mid_stagger_types": ["col_h9_r1"]}, "col_h9_r0_p2__t1__cl0045af7b")
    monkeypatch.setenv("OT_RELAY_MID_STAGGER", "1")
    assert gen_phys._relay_mid_stagger({}, "anything__t1")


def test_tcl_stagger_guarded():
    s = (HERE / "relay_mid.tcl").read_text()
    assert 'set rm_stag [expr {[info exists ::env(OT_RELAY_MID_STAGGER)] && $::env(OT_RELAY_MID_STAGGER) eq "1"}]' in s
    assert "if {$rm_stag} {" in s
    g = (HERE / "gen_phys.py").read_text()
    assert '"export OT_RELAY_MID_STAGGER = 1"' in g
