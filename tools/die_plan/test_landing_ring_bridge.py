"""KIT-OPS-6 11-14 (FABLE-TYPES-KV cause 1): landing ring-band bridge.
  (a) a ring that runs out of band retries with the band grown up to +10 % area (rolled back between tries);
  (b) START-window / local-reset cells keep out of other groups' ring bands (fallback: the old search);
  (c) the group loop names EVERY failing band in one pass.
    python3 -m pytest -q tools/die_plan/test_landing_ring_bridge.py"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TCL = (HERE / "landing_placement.tcl").read_text()
needs_tcl = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")


def proc(name):
    m = re.search(r"proc %s \{[^\n]*\} \{\n.*?\n\}\n" % re.escape(name), TCL, re.S)
    assert m, name
    return m.group(0)


def run(body):
    return subprocess.run(["tclsh"], input=body, capture_output=True, text=True, check=True).stdout


HEAD = r"""
set ff_x0 0; set ff_y0 0; set ff_x1 2000; set ff_y1 2700; set ff_rh 270; set ff_sw 54; set ff_dbu 1000
"""


@needs_tcl
def test_grow_steps_stay_within_ten_percent_and_follow_the_thin_axis():
    body = HEAD + proc("cland_ring_grows") + r"""
foreach r [cland_ring_grows {0 0 20 2.7}] {
  lassign $r ax ay bx by
  puts "G [expr {($bx-$ax)*($by-$ay)/(20*2.7)}]"
}
puts "T [cland_ring_grows {0 0 2.7 20}]"
puts "Z [cland_ring_grows {0 0 20 0.0}]"
"""
    out = run(body)
    areas = [float(x) for x in re.findall(r"^G (\S+)", out, re.M)]
    assert areas and all(1.0 < a <= 1.1000001 for a in areas), out
    assert len(areas) >= 2          # high side +10 % (one row step on a 10-row band) and the low-side variant
    tall = re.search(r"^T (.*)$", out, re.M).group(1)
    assert tall.startswith("{0 0 2.808")    # a tall band grows in x by whole sites
    assert re.search(r"^Z $", out, re.M)


STUB_PLACE = r"""
set cland_done [dict create]; set cland_n 0; set cland_cursor {}; set cland_col_cursor {}; set cland_occ [dict create]
set cland_fh [open /tmp/k6_ring_rec_[pid].txt w+]
proc ins {nm op args} { switch $op { setPlacementStatus { set ::status($nm) [lindex $args 0] } default {} } }
proc blk {op args} { set nm [lindex $args 0]; interp alias {} I$nm {} ins $nm; return I$nm }
set ff_blk blk
# stub placement: 40 cells need band height >= NEED; places (and records) cells one by one, fails on the last
proc cland_place_ff {prefix rect tag} {
 global cland_done cland_n cland_fh
 lassign $rect ax ay bx by
 for {set k 0} {$k < 40} {incr k} {
  if {$k == 39 && ($by-$ay) < $::NEED} { error "OT_CLAND no legal nonoverlapping row/site in reserved band for $prefix/c$k ($tag)" }
  dict set cland_done $prefix/c$k 1; incr cland_n
  set ::status($prefix/c$k) FIRM
  puts $cland_fh "$prefix/c$k\tcland:$tag\t$ay"
 }
 return 40
}
"""


def ring(need, rect="{0 0 20 2.7}"):
    return HEAD + proc("cland_ring_grows") + proc("cland_ring_place") + STUB_PLACE + (
        "set NEED %s\nset rc [catch {cland_ring_place g %s ring:g+ff} msg]\n"
        "puts \"RC $rc N $cland_n DONE [dict size $cland_done]\"\nputs \"MSG $msg\"\n"
        "flush $cland_fh; seek $cland_fh 0; set txt [read $cland_fh]; puts \"REC [llength [split [string trim $txt] \\n]]\"\n"
        "puts \"BAD [llength [array names status -glob */c*]]\"\n"
        "set nf 0; foreach k [array names status] { if {$status($k) eq {NONE}} { incr nf } }; puts \"NONE $nf\"\n"
    ) % (need, rect)


@needs_tcl
def test_ring_that_fits_the_plan_band_is_untouched():
    out = run(ring(2.7))
    assert "RC 0 N 40 DONE 40" in out and "REC 40" in out and "ring grow" not in out


@needs_tcl
def test_ring_tail_takes_a_grown_band_and_rolls_back_the_failed_tries():
    out = run(ring(2.8))            # +3.7 % needed: the one-row (+10 %) step fits
    assert "RC 0 N 40 DONE 40" in out, out
    assert "ring grow g (ring:g+ff)" in out and "REC 40" in out      # records of the failed tries were discarded


@needs_tcl
def test_ring_beyond_ten_percent_fails_with_the_original_error_and_leaves_no_cells():
    out = run(ring(3.2))
    assert "RC 1 N 0 DONE 0" in out, out
    assert "OT_CLAND no legal nonoverlapping row/site in reserved band for g/c39" in out
    assert "REC 0" in out


@needs_tcl
def test_start_cells_keep_out_of_other_ring_bands_and_fall_back_when_inside_one():
    mock = r"""
set cland_done {}; set cland_n 0; set cland_cursor {}
set cland_fh [open /dev/null w]
set cland_occ [dict create]
set ff_orient [dict create 0 R0 270 MX 540 R0 810 MX 1080 R0 1350 MX 1620 R0 1890 MX 2160 R0 2430 MX]
set ::W 108
proc mst {op args} { switch $op { getWidth { return 108 } getHeight { return 270 } isBlock { return 0 } getName { return BUFx2 } } }
proc ins {k op args} { switch $op { getName { return u_cland_s/c$k } getMaster { return mst } getPlacementStatus { return PLACED } setLocation { set ::loc($k) $args } default {} } }
interp alias {} i1 {} ins 1
interp alias {} i2 {} ins 2
set ff_blk {}
set cland_ring_done [dict create]
set cland_ring_bands [list [list other ring:o+ff {0 0 1.0 1.08}]]
# START window 0..1.0 um wide x 1.08 tall covers the ring band exactly; a second wider window has room beside it
set r1 [catch {cland_avoid_rings g {cland_put i1 {0 0 4.0 1.08} writer-start:x}} e1]
puts "R1 $r1 X $::loc(1)"
set r2 [catch {cland_avoid_rings g {cland_put i2 {0 0 1.0 1.08} writer-start:y}} e2]
puts "R2 $r2 X $::loc(2)"
puts "BLOCK [info exists ::cland_block]"
"""
    body = HEAD.replace("ff_y1 2700", "ff_y1 2700") + proc("cland_group_insts") + proc("cland_occupy") + proc("cland_put") \
        + proc("cland_band_rects") + proc("cland_avoid_rings") + mock
    out = run(body)
    x1 = int(re.search(r"R1 0 X (\d+) (\d+)", out).group(1))
    assert x1 >= 1000, out                 # beside the 1.0-um ring band, not inside it
    assert "R2 0" in out                   # a window inside the band falls back to the old search
    assert "BLOCK 0" in out


@needs_tcl
def test_group_loop_names_every_failing_band():
    seg = re.search(r"set cland_multi_seen \{\}\n.*?\nclose \$cland_fh\n", TCL, re.S).group(0)
    mock = HEAD + proc("cland_band_rects") + proc("cland_band_need") + r"""
set cland_multi [dict create]
set cland_fh [open /dev/null w]
set cland_done {}
proc cland_group_insts {prefix} { return [list m_$prefix] }
proc mm {op args} { switch $op { getWidth { return 108 } getHeight { return 270 } isBlock { return 0 } getName { return BUFx2 } } }
proc im {nm op args} { switch $op { getName { return $nm } getMaster { return mm } getPlacementStatus { return PLACED } } }
interp alias {} m_bad1 {} im m_bad1; interp alias {} m_bad2 {} im m_bad2; interp alias {} m_ok {} im m_ok
proc cland_band_fit {prefix rect tag} { if {[string match bad* $prefix]} { error "OT_CLAND no legal nonoverlapping row/site in reserved band for $prefix ($tag): checked before placement" } }
proc cland_put {args} { if {[info exists ::cland_fill_dry]} { incr ::drycalls }; return }
set drycalls 0
set cland_groups [list [list bad1 {0 0 2 2} x:1] [list ok {0 0 2 2} y:1] [list bad2 {0 0 4 2} z:1]]
set rc [catch {
""" + seg + r"""
} err]
puts "RC $rc"
puts "ERR $err"
puts "DRY [info exists ::cland_fill_dry] CALLS $drycalls"
"""
    # the segment references procs of the real file that this mock does not need
    for name in ("cland_avoid_rings", "cland_ring_place", "cland_ring_grows"):
        mock = proc(name) + mock
    out = run(mock)
    assert out.count("OT_CLAND BAND FAIL") == 2, out
    assert "BAND FAIL bad1 (x:1): 1 cells" in out and "BAND FAIL bad2 (z:1): 1 cells" in out
    assert re.search(r"RC 1\nERR OT_CLAND no legal nonoverlapping row/site in reserved band for bad1", out), out
    assert "DRY 0" in out
