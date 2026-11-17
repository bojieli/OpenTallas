"""S81-COL-SSTN-M5 11-17 (FABLE-PD-S81-0720 B3): M5 routing block over ot_s81_sstn_* cores from floorplan, opt-in, idempotent."""
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
HOOK = HERE / "sstn_m5_block.tcl"

MOCK = r'''
namespace eval ord {}
proc ord::get_db_block {} { return blk }
proc ord::get_db_tech {} { return tech }
set OBS {}
proc tech {op args} { if {$op eq "getDbUnitsPerMicron"} { return 1000 }; if {$op eq "findLayer"} { return ly_[lindex $args 0] } }
proc ly_M5 {op} { return M5 }
proc blk {op} { global OBS; switch $op { getObstructions { set r {}; set i 0; foreach o $OBS { lappend r ob$i; incr i }; return $r } getInsts { return {c1 c2 f1} } } }
foreach {n m x0 y0 x1 y1} {c1 ot_s81_sstn_base566 10000 20000 94240 50240  c2 ot_s81_sstn_tiny 0 0 6000 3000  f1 DFFHQNx1_ASAP7_75t_R 0 0 1000 1000} {
  proc $n {op} "switch \$op { getName { return $n } getMaster { return m_$n } getBBox { return bb_$n } }"
  proc m_$n {op} "return $m"
  proc bb_$n {op} "switch \$op { xMin { return $x0 } yMin { return $y0 } xMax { return $x1 } yMax { return $y1 } }"
}
proc odb::dbObstruction_create {b ly x0 y0 x1 y1} { global OBS; lappend OBS [list $ly $x0 $y0 $x1 $y1] }
namespace eval odb {}
'''


def _run(body=""):
    if not shutil.which("tclsh"):
        pytest.skip("no tclsh")
    src = MOCK.replace("proc odb::dbObstruction_create", "namespace eval odb {}\nproc odb::dbObstruction_create") + "\nsource {" + str(HOOK) + "}\n" + body
    r = subprocess.run(["tclsh"], input=src, text=True, capture_output=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


def test_blocks_only_sstn_core_interior_with_the_inset():
    out = _run("puts \"N [llength $OBS] [lindex $OBS 0]\"\n")
    assert "OT_SSTN_M5_BLOCK c1 ot_s81_sstn_base566 M5 14.000 22.000 90.240 48.240" in out, out
    assert "skip c2: inset leaves no interior" in out and "N 1 ly_M5 14000 22000 90240 48240" in out, out
    assert "done: 1 obstructions over 2 ot_s81_sstn_* cores" in out, out


def test_idempotent_second_run_adds_nothing():
    out = _run("ot_sstn_m5_block\nputs \"N [llength $OBS]\"\n")
    assert "N 1" in out, out


def test_opt_in_wiring_and_staging():
    ff = (HERE / "face_flops.tcl").read_text()
    assert 'OT_S81_SSTN_M5_BLOCK) eq "1"' in ff and "/work/sstn_m5_block.tcl" in ff
    gp = (HERE / "gen_phys.py").read_text()
    assert '"sstn_m5_block.tcl"' in gp and 'export OT_S81_SSTN_M5_BLOCK = 1' in gp
