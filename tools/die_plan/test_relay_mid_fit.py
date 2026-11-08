"""relay_mid.tcl FIT (opt-in OT_RELAY_MID_FIT=1) and gutter_block.tcl (opt-in OT_GUTTER_BLOCK_UM), S81-TYPES-5 11-07.
COLH10 vR: relay clusters sat in the 40-um macro channel because the old fallback takes the nearest free POINT; t56: high
-fanout drivers sat in the LN-column gutter.  Two macros 40 um apart (x 700..740, y 600..800); one relay stage from a
FIRM source (720,450) to a FIRM sink (720,950): its midpoint (720,700) lies in the channel.
Needs docker + openroad/orfs:asap7lock (skipped otherwise).   python3 -m pytest -q tools/die_plan/test_relay_mid_fit.py"""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
FF = "DFFHQNx1_ASAP7_75t_R"
W = 64

LEF = """VERSION 5.8 ;
BUSBITCHARS "[]" ;
DIVIDERCHAR "/" ;
MACRO blk
  CLASS BLOCK ;
  ORIGIN 0 0 ;
  SIZE 100 BY 200 ;
  PIN a
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER M4 ;
        RECT 0 0 0.024 0.5 ;
    END
  END a
  OBS
    LAYER M1 ;
      RECT 0 0 100 200 ;
  END
END blk
END LIBRARY
"""


def _netlist():
    v = ["module t(input wire clk, input wire a);"]
    v += [f"  wire s{k}, r{k};" for k in range(W)]
    v.append("  blk m1 (.a(a));\n  blk m2 (.a(a));")
    for k in range(W):
        v.append(f"  {FF} src{k} (.CLK(clk), .D(a), .QN(s{k}));")
        v.append(f"  {FF} \\u_y_a.r[{k}]  (.CLK(clk), .D(s{k}), .QN(r{k}));")
        v.append(f"  {FF} snk{k} (.CLK(clk), .D(r{k}), .QN());")
    v.append("endmodule\n")
    return "\n".join(v)


TCL = r"""
set P /OpenROAD-flow-scripts/flow/platforms/asap7/lef
read_lef $P/asap7_tech_1x_201209.lef
read_lef $P/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /w/blk.lef
read_verilog /w/t.v
link_design t
initialize_floorplan -die_area "0 0 1500 1200" -core_area "5 5 1495 1195" -site asap7sc7p5t
set blk [ord::get_db_block]
set u [[ord::get_db_tech] getDbUnitsPerMicron]
foreach i [$blk getInsts] {
  set n [$i getName]
  if {$n eq "m1"} { $i setLocation [expr {600 * $u}] [expr {600 * $u}]; $i setPlacementStatus FIRM
  } elseif {$n eq "m2"} { $i setLocation [expr {740 * $u}] [expr {600 * $u}]; $i setPlacementStatus FIRM
  } elseif {[string match src* $n]} { $i setLocation [expr {720 * $u}] [expr {450 * $u}]; $i setPlacementStatus FIRM
  } elseif {[string match snk* $n]} { $i setLocation [expr {720 * $u}] [expr {950 * $u}]; $i setPlacementStatus FIRM
  } else { $i setLocation [expr {100 * $u}] [expr {110 * $u}]; $i setPlacementStatus PLACED }
}
set ::env(RESULTS_DIR) /w
set ::env(OT_RELAY_MID_RE) {^(u_y_[a-z]+)[.]}
source /w/relay_mid.tcl
source /w/gutter_block.tcl
foreach i [$blk getInsts] {
  set n [string map {\\ {}} [$i getName]]
  if {[regexp {^u_y_a} $n]} {
    set b [$i getBBox]
    puts "CHK [expr {[$b xMin] / double($u)}] [expr {[$b yMin] / double($u)}] [$i getPlacementStatus]"
  }
}
foreach k [$blk getBlockages] { set b [$k getBBox]
  puts "BLK [expr {[$b xMin] / double($u)}] [expr {[$b yMin] / double($u)}] [expr {[$b xMax] / double($u)}] [expr {[$b yMax] / double($u)}]" }
"""


def _run(env):
    if not shutil.which("docker"):
        pytest.skip("no docker")
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "t.v").write_text(_netlist())
        (Path(d) / "blk.lef").write_text(LEF)
        (Path(d) / "t.tcl").write_text(TCL)
        shutil.copy(HERE / "relay_mid.tcl", d)
        shutil.copy(HERE / "gutter_block.tcl", d)
        envs = []
        for k, v in env.items():
            envs += ["-e", f"{k}={v}"]
        cmd = "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /w/t.tcl; chmod -R a+rwX /w"
        r = subprocess.run(["docker", "run", "--rm", "--memory=4g", "--memory-swap=4g", *envs, "-v", f"{d}:/w",
                            "openroad/orfs:asap7lock", "bash", "-lc", cmd], capture_output=True, text=True, timeout=600)
        if r.returncode and "Unable to find image" in r.stderr:
            pytest.skip("image missing")
        out = r.stdout
        assert f"OT_RELAY_MID placed {W} relay flops of 1 stations" in out, out[-3000:]
        pos = [(float(x), float(y)) for x, y, st in re.findall(r"CHK ([0-9.]+) ([0-9.]+) (\w+)", out)]
        blk = [tuple(map(float, b)) for b in re.findall(r"BLK ([0-9.]+) ([0-9.]+) ([0-9.]+) ([0-9.]+)", out)]
        assert len(pos) == W
        return out, pos, blk


def _in_channel(x, y):
    return 700 <= x <= 740 and 600 <= y <= 800


def test_default_unchanged_sits_in_channel():
    out, pos, blk = _run({})
    assert "OT_RELAY_MID_FIT" not in out and "OT_GUTTER_BLOCK" not in out
    assert blk == []
    assert sum(_in_channel(x, y) for x, y in pos) == W       # the old smell, kept byte-for-byte by default


def test_fit_leaves_channel_and_keeps_hops():
    out, pos, blk = _run({"OT_RELAY_MID_FIT": "1"})
    assert "OT_RELAY_MID_FIT fitted 1 stations, 0 on the old fallback" in out, out[-2000:]
    assert not any(_in_channel(x, y) for x, y in pos)
    for x, y in pos:
        assert abs(y - 450) + abs(x - 720) <= 405 + 30 and abs(y - 950) + abs(x - 720) <= 405 + 30
        assert y <= 600 - 8.64 - 20 + 1 or y >= 800 + 8.64 + 20 - 2   # footprint clears halo + channel margin


def test_gutter_block_only_under_threshold():
    out, pos, blk = _run({"OT_GUTTER_BLOCK_UM": "45"})
    assert blk == [(700.0, 600.0, 740.0, 800.0)], blk
    assert "OT_GUTTER_BLOCK 1 gutter placement blockages" in out
    out, pos, blk = _run({"OT_GUTTER_BLOCK_UM": "30"})
    assert blk == [] and "OT_GUTTER_BLOCK 0 gutter" in out
