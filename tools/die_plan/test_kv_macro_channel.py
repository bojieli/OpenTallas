"""KV-KITS-9 10-28: results/kv_kits_8_1028/macro_channel.py -- channel rects from the kit macro sites, and the generated
Tcl removes fixed tap/endcap physical cells inside a channel (common macro_channel_block.tcl rule) while a fixed
logic cell or a macro still stops the kit.  The Tcl runs under tclsh against a minimal odb mock."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "results/kv_kits_8_1028/macro_channel.py"
TCLSH = shutil.which("tclsh")

# two 20x10 macros 11 um apart (x 0..20 and 31..51): one vertical channel rect 20..31 x 0..10
MACRO_PLACE = "foreach {master sites} {m_test {{0 0 R0} {31 0 R0}}} {\n}\n"
LEF = "MACRO m_test\n  SIZE 20 BY 10 ;\nEND m_test\n"

MOCK = r"""
set ::destroyed {}
proc mk_inst {name type status x0 y0 x1 y1 block} {
  set ::I($name) [list $type $status $x0 $y0 $x1 $y1 $block]
  proc ::inst_$name {args} [string map [list @N $name] {
    lassign $::I(@N) type status x0 y0 x1 y1 block
    switch [lindex $args 0] {
      getPlacementStatus {return $status}
      getName {return @N}
      getMaster {return ::master_@N}
      getBBox {return ::bbox_@N}
    }
  }]
  proc ::master_$name {args} [string map [list @N $name] {
    lassign $::I(@N) type status x0 y0 x1 y1 block
    switch [lindex $args 0] { getType {return $type} isBlock {return $block} }
  }]
  proc ::bbox_$name {args} [string map [list @N $name] {
    lassign $::I(@N) type status x0 y0 x1 y1 block
    switch [lindex $args 0] { xMin {return $x0} yMin {return $y0} xMax {return $x1} yMax {return $y1} }
  }]
}
proc ::blk {args} {
  set r {}
  foreach n [lsort [array names ::I]] { if {[lsearch $::destroyed $n] < 0} { lappend r ::inst_$n } }
  return $r
}
proc ::tech {args} {return 1000}
namespace eval ord { proc get_db_block {} {return ::blk}; proc get_db_tech {} {return ::tech} }
namespace eval odb {
  proc dbBlockage_create {args} {lappend ::blockages [lrange $args 1 end]; return 1}
  proc dbInst_destroy {i} {lappend ::destroyed [string range $i 7 end]}
}
set ::blockages {}
"""


def _kit(tmp_path):
    kd = tmp_path / "kit"
    (kd / "macros").mkdir(parents=True)
    (kd / "macro_place.tcl").write_text(MACRO_PLACE)
    (kd / "macros/m_test.lef").write_text(LEF)
    (kd / "pv_tree_pre_gpl.tcl").write_text("# pre gpl\n")
    out = subprocess.run([sys.executable, "-I", str(TOOL), str(kd)], capture_output=True, text=True, check=True)
    return kd, json.loads(out.stdout)


def test_channel_rect_and_source_line(tmp_path):
    kd, rep = _kit(tmp_path)
    assert rep["rects"] == [[20.0, 0.0, 31.0, 10.0]]
    assert (kd / "pv_tree_pre_gpl.tcl").read_text().count("source /work/macro_channel_blk.tcl") == 1
    _kit_again = subprocess.run([sys.executable, "-I", str(TOOL), str(kd)], capture_output=True, text=True, check=True)
    assert (kd / "pv_tree_pre_gpl.tcl").read_text().count("source /work/macro_channel_blk.tcl") == 1


def _run(kd, insts):
    script = MOCK + "".join(f"mk_inst {' '.join(map(str, i))}\n" for i in insts) + \
        f"source {kd / 'macro_channel_blk.tcl'}\nputs \"DESTROYED [lsort $::destroyed]\"\nputs \"NB [llength $::blockages]\"\n"
    f = kd / "mock_run.tcl"
    f.write_text(script)
    return subprocess.run([TCLSH, str(f)], capture_output=True, text=True)


@pytest.mark.skipif(TCLSH is None, reason="tclsh not installed")
def test_endcap_and_tap_removed_logic_kept(tmp_path):
    kd, _ = _kit(tmp_path)
    r = _run(kd, [("PHY_EDGE_ROW_1_Right_7", "ENDCAP_PRE", "FIRM", 20500, 0, 21000, 270, 0),
                  ("TAP_3", "CORE_WELLTAP", "FIRM", 25000, 270, 25500, 540, 0),
                  ("u_logic", "CORE", "PLACED", 40000, 0, 41000, 270, 0),        # outside the channel
                  ("u_far_tap", "CORE_WELLTAP", "FIRM", 60000, 0, 60500, 270, 0)])  # outside: kept
    assert r.returncode == 0, r.stderr
    assert "DESTROYED PHY_EDGE_ROW_1_Right_7 TAP_3" in r.stdout and "NB 1" in r.stdout
    assert "1 tap/endcap physical cells removed" not in r.stdout and "2 tap/endcap physical cells removed" in r.stdout


@pytest.mark.skipif(TCLSH is None, reason="tclsh not installed")
@pytest.mark.parametrize("inst", [("u_ff", "CORE", "FIRM", 22000, 0, 23000, 270, 0),
                                  ("u_mac", "BLOCK", "FIRM", 24000, 0, 26000, 2000, 1)])
def test_fixed_logic_or_macro_still_stops(tmp_path, inst):
    kd, _ = _kit(tmp_path)
    r = _run(kd, [inst])
    assert r.returncode != 0 and "KV macro channel" in r.stderr
