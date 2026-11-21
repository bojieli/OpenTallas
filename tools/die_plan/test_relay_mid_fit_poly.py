"""relay_mid.tcl FIT POLY (FAM-S81-COL-H10-R3 11-21, FABLE-CLOSURE-STRATEGY lever 2 fix 1): with OT_RELAY_POLY=1 a chain whose
source-sink line crosses a hard core is placed on a polyline, and that branch never recorded the stage for FIT, so FIT
counted no group on every col kit (col_h10_r0_p1 pvb095fa2f: 157 stations in 90 polyline chains, "OT_RELAY_MID_FIT fitted 0
stations", OT_HOOK_COVERAGE touched=0 expected=0).  One 100 x 200 um macro (x 670..770, y 600..800) sits across the line of
one relay stage from FIRM sources at (720, 450) to FIRM sinks at (720, 950).  STAGGER + FIT: parallel FIT chains keep their
stagger offset instead of collapsing onto one FIT seat.
Needs docker + openroad/orfs:asap7lock (skipped otherwise).   python3 -m pytest -q tools/die_plan/test_relay_mid_fit_poly.py"""
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


def _netlist(groups):
    v = ["module t(input wire clk, input wire a);"]
    v.append("  blk m1 (.a(a));")
    for g in groups:
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
read_lef /w/blk.lef
read_verilog /w/t.v
link_design t
initialize_floorplan -die_area "0 0 1500 1200" -core_area "5 5 1495 1195" -site asap7sc7p5t
set blk [ord::get_db_block]
set u [[ord::get_db_tech] getDbUnitsPerMicron]
foreach i [$blk getInsts] {
  set n [$i getName]
  if {$n eq "m1"} { $i setLocation [expr {670 * $u}] [expr {600 * $u}]; $i setPlacementStatus FIRM
  } elseif {[regexp {^[a-z]src} $n]} { $i setLocation [expr {720 * $u}] [expr {450 * $u}]; $i setPlacementStatus FIRM
  } elseif {[regexp {^[a-z]snk} $n]} { $i setLocation [expr {720 * $u}] [expr {950 * $u}]; $i setPlacementStatus FIRM
  } else { $i setLocation [expr {100 * $u}] [expr {110 * $u}]; $i setPlacementStatus PLACED }
}
set ::env(RESULTS_DIR) /w
set ::env(OT_RELAY_MID_RE) {^(u_y_[a-z]+)[.]}
source /w/relay_mid.tcl
foreach i [$blk getInsts] {
  set n [string map {\\ {}} [$i getName]]
  if {[regexp {^u_y_([a-z])} $n -> g]} {
    set b [$i getBBox]
    puts "CHK $g [expr {[$b xMin] / double($u)}] [expr {[$b yMin] / double($u)}]"
  }
}
"""


def _run(env, groups="a"):
    if not shutil.which("docker"):
        pytest.skip("no docker")
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "t.v").write_text(_netlist(groups))
        (Path(d) / "blk.lef").write_text(LEF)
        (Path(d) / "t.tcl").write_text(TCL)
        shutil.copy(HERE / "relay_mid.tcl", d)
        envs = []
        for k, v in {"OT_RELAY_POLY": "1", **env}.items():
            envs += ["-e", f"{k}={v}"]
        cmd = "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /w/t.tcl; chmod -R a+rwX /w"
        r = subprocess.run(["docker", "run", "--rm", "--memory=4g", "--memory-swap=4g", *envs, "-v", f"{d}:/w",
                            "openroad/orfs:asap7lock", "bash", "-lc", cmd], capture_output=True, text=True, timeout=600)
        if r.returncode and "Unable to find image" in r.stderr:
            pytest.skip("image missing")
        out = r.stdout
        n = len(groups)
        assert f"OT_RELAY_MID placed {n * W} relay flops of {n} stations" in out, out[-3000:]
        assert f"OT_RELAY_POLY chain u_y_{groups[0]}..u_y_{groups[0]} (1 stations)" in out, out[-3000:]
        pos = {g: [] for g in groups}
        for g, x, y in re.findall(r"CHK ([a-z]) ([0-9.]+) ([0-9.]+)", out):
            pos[g].append((float(x), float(y)))
        assert all(len(p) == W for p in pos.values())
        return out, pos


def _clear_of_macro(x, y, m=8.64):
    return not (670 - m <= x <= 770 + m and 600 - m <= y <= 800 + m)


def test_fit_poly_off_reproduces_the_zero_count():
    # the pre-fix selector: a polyline stage is not a FIT group, so FIT counts nothing (col kits: fitted 0, expected=0)
    out, pos = _run({"OT_RELAY_MID_FIT": "1", "OT_RELAY_MID_FIT_POLY": "0"})
    assert "OT_RELAY_MID_FIT fitted 0 stations, 0 on the old fallback" in out, out[-2000:]
    assert "touched=0 expected=0" in out
    assert "OT_RELAY_MID_FIT_POLY" not in out


def test_fit_poly_fits_polyline_stage():
    out, pos = _run({"OT_RELAY_MID_FIT": "1"})
    assert "OT_RELAY_MID_FIT fitted 1 stations, 0 on the old fallback" in out, out[-2000:]
    assert "OT_RELAY_MID_FIT_POLY 1 of the fitted stations on polylines, 0 polyline stage(s) short of depth" in out
    assert "touched=1 expected=1 fallback=0 depth_fallback=0 poly_depth_fallback=0" in out
    for x, y in pos["a"]:
        assert _clear_of_macro(x, y), (x, y)
        # both legs within the 405-um reach along the detour around the macro (Manhattan to each end is a lower bound)
        assert abs(x - 720) + abs(y - 450) <= 405 + 40 and abs(x - 720) + abs(y - 950) <= 405 + 40


def test_fit_poly_depth_short_stage_stays_advisory():
    # a 200-um reach cannot seat a 1-stage ~600-um detour: the stage takes the fallback, counted as poly depth (the
    # polyline depth gate is OT_RELAY_POLY_FAIL), so OT_RELAY_FALLBACK_MAX_FRAC=0 does not newly stop place
    out, pos = _run({"OT_RELAY_MID_FIT": "1", "OT_RELAY_MID_MAX_HOP_UM": "200", "OT_RELAY_FALLBACK_MAX_FRAC": "0"})
    assert "OT_RELAY_MID_FIT fitted 0 stations, 1 on the old fallback" in out, out[-2000:]
    assert "depth_fallback=0 poly_depth_fallback=1" in out


def test_stagger_offsets_survive_fit():
    # two parallel polyline chains: with FIT the offsets are kept on the FIT seat, the clusters do not share one seat
    out, pos = _run({"OT_RELAY_MID_FIT": "1", "OT_RELAY_MID_STAGGER": "1"}, groups="ab")
    assert "OT_RELAY_MID_STAGGER sets 1 chains moved 2" in out, out[-2000:]
    assert "OT_RELAY_MID_FIT fitted 2 stations, 0 on the old fallback" in out, out[-2000:]
    xa = [x for x, _ in pos["a"]]; xb = [x for x, _ in pos["b"]]
    ya = [y for _, y in pos["a"]]; yb = [y for _, y in pos["b"]]
    gap = max(min(xb) - max(xa), min(xa) - max(xb), min(yb) - max(ya), min(ya) - max(yb))
    assert gap >= 15.0, (min(xa), max(xa), min(xb), max(xb), min(ya), max(ya), min(yb), max(yb))
    for x, y in pos["a"] + pos["b"]:
        assert _clear_of_macro(x, y), (x, y)


def test_tcl_fit_poly_guarded():
    s = (HERE / "relay_mid.tcl").read_text()
    assert 'set rm_fit_poly [expr {[info exists ::env(OT_RELAY_MID_FIT)] && $::env(OT_RELAY_MID_FIT) eq "1"' in s
    assert "dict set rm_seg $c [list $ax $ay $bx $by $j $n $rm_w0 $rm_W $rm_pts]" in s
