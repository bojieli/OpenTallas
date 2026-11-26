"""DRT-TAIL-3 (QC-DRT-TAIL 11-25): pg_track_truth.tcl ot_pgtt_add_m3 adds temporary GRT obstructions over the M3 tracks that are
spacing-illegal next to the M3 pad of every M2..M5 PG via stack (sle_fe_v1 cl1cbb7497 / slw_fe_v1 cl95cd1d0c, cldb4efe33: 3 nm slivers at the
M5 strap residues).  Run with tclsh against fake odb objects; default on, OT_PG_TRACK_TRUTH_M3=0 off."""
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TCLSH = shutil.which("tclsh")

FAKE = r"""
proc fake {name d} { set ::fk($name) $d; proc $name {m args} "global fk; dict get \$fk($name) \$m" }
proc ::ord::get_db_block {} {}
# --- layer M3: vertical, width 18, spacing 18, 1 um = 1000 dbu, tracks 9 + 36 n
fake L3 {getType ROUTING getRoutingLevel 3 getDirection VERTICAL getWidth 18 getSpacing 18 getName M3}
fake L4 {getType ROUTING getRoutingLevel 4 getDirection HORIZONTAL getWidth 18 getSpacing 18 getName M4}
fake TECH {getLayers {L3 L4}}
set grid {}; for {set i 0} {$i < 400} {incr i} { lappend grid [expr {9 + 36 * $i}] }
fake TG [list getGridX $grid]
# via: M3 pad -45..45 x -17..17, M4 box -60..60 x -20..20 (union min -60,-20)
fake BM3 {getTechLayer L3 xMin -45 yMin -17 xMax 45 yMax 17}
fake BM4 {getTechLayer L4 xMin -60 yMin -20 xMax 60 yMax 20}
fake VIA {getName v34 getBoxes {BM3 BM4}}
# via origins (x 5000, y 1000 / 1540): SBox bbox = origin + union
fake W1 {isVia 1 getTechVia NULL getBlockVia VIA xMin 4940 yMin 980 xMax 5060 yMax 1020}
fake W2 {isVia 1 getTechVia NULL getBlockVia VIA xMin 4940 yMin 1520 xMax 5060 yMax 1560}
fake SW {getWires {W1 W2}}
fake NET {isSpecial 1 getSigType POWER getSWires SW}
fake BLK {getNets NET findTrackGrid TG getDieArea DIE getDbUnitsPerMicron 1000}
fake DIE {xMin 0 yMin 0 xMax 10000 yMax 10000}
proc BLK_stub {} {}
set ::made {}
proc odb::dbObstruction_create {blk L x0 y0 x1 y1} { lappend ::made [list [$L getName] $x0 $y0 $x1 $y1]; return obs[llength $::made] }
"""


def _run(extra=""):
    src = (HERE / "pg_track_truth.tcl").read_text()
    s = "namespace eval odb {}\nnamespace eval ord {}\n" + FAKE + src + "\nset ::ot_pgtt_obs {}\n" + extra + \
        "\not_pgtt_add_m3 BLK TECH\nputs \"MADE $::made\"\nputs \"OBS [llength $::ot_pgtt_obs]\"\n"
    r = subprocess.run([TCLSH], input=s, capture_output=True, text=True)
    assert r.returncode == 0 and not r.stderr, r.stderr + r.stdout
    return r.stdout


@pytest.mark.skipif(not TCLSH, reason="tclsh")
def test_m3_pad_gets_one_obstruction_over_the_illegal_tracks_and_pad_rows():
    out = _run("set ::env(OT_PG_TRACK_TRUTH_M3) 1")
    assert "1 pad columns on M3" in out
    # pad x 4955..5045, hw 9, sp 18: illegal when 4955-27 < t < 5045+27 -> tracks 4941..5069 exclusive: 4977 5013 (+4941? no: 4928<4941<5072 yes)
    tracks = [t for t in (9 + 36 * i for i in range(400)) if 4955 - 27 < t < 5045 + 27]
    made = [l for l in out.splitlines() if l.startswith("MADE")][0]
    assert f"M3 {tracks[0] - 9} 983 {tracks[-1] + 9} 1557" in made.replace("{", "").replace("}", "")
    assert "OBS 1" in out                # one column, both pad rows merged into one y range


@pytest.mark.skipif(not TCLSH, reason="tclsh")
def test_m3_pad_off_knob_adds_nothing():
    out = _run("set ::env(OT_PG_TRACK_TRUTH_M3) 0")
    assert "OBS 0" in out and "pad columns" not in out


def test_m3_called_from_ot_pgtt_add_in_both_modes_and_default_off():
    t = (HERE / "pg_track_truth.tcl").read_text()
    assert "ot_pgtt_add_m3 $blk $tech" in t
    i = t.index("ot_pgtt_add_m3 $blk $tech")
    assert t.index("if {[ot_pgtt_region_mode]} {", i) > i       # called before the region-mode early return
    assert "OBS 0" in _run("unset -nocomplain ::env(OT_PG_TRACK_TRUTH_M3)")
