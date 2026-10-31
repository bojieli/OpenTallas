"""AUTOBUILD-PIPE-2 10-31 (S81 slice_station wave: every place FAIL was 'no legal ... (collector:rst_rl_N)'): a reset
collector cell without a site in its relay window (+-2.16 um; several relays on one xy, or the relay inside a ring
band the FIRM ring fill took) takes the window grown about the same centre x2/x4/x8; with no site even there it fails
closed with the same error.  Runs the REAL cland_put / cland_occupy / cland_put_collector procs (OpenDB mocked)."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

TCL = Path(__file__).with_name("landing_placement.tcl").read_text()
needs_tcl = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")


def _procs():
    put = re.search(r"proc cland_put \{i rect tag \{sp \{\}\} \{cur 0\}\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    occ = re.search(r"proc cland_occupy \{x y w h\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    grow = re.search(r"proc cland_put_collector \{i rect tag\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    return occ + put + grow


# 40 rows x 40000 dbu core (40 x 10.8 um), site 54, row 270; collector window +-2.16 um about (20, 5.4) um
MOCK = r"""
set ff_x0 0; set ff_y0 0; set ff_x1 40000; set ff_y1 10800; set ff_rh 270; set ff_sw 54; set ff_dbu 1000
set ff_orient [dict create]; for {set r 0} {$r < 40} {incr r} { dict set ff_orient [expr {$r*270}] R0 }
set cland_done {}; set cland_n 0; set cland_cursor {}; set cland_fh [open /dev/null w]
set cland_occ [dict create]
# foreign occupancy: every row, x in [OL, OU) dbu
for {set r 0} {$r < 40} {incr r} { dict lappend cland_occ $r [list %(OL)d %(OU)d] }
set ::loc {}
proc m0 {op args} { switch $op { getWidth { return 108 } getHeight { return 270 } isBlock { return 0 } getName { return DFFx1 } } }
proc c0 {op args} { switch $op { getName { return u_cland_collect_rst_rl_1/q } getMaster { return m0 }
  getPlacementStatus { return PLACED } setLocation { set ::loc $args } default {} } }
if {[catch {cland_put_collector c0 {17.84 3.24 22.16 7.56} collector:rst_rl_1} e]} { puts "ERR $e" } else { puts "LOC $::loc" }
"""


def _run(ol, ou):
    out = subprocess.run(["tclsh"], input=_procs() + MOCK % dict(OL=ol, OU=ou), capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return out.stdout


@needs_tcl
def test_free_window_places_inside_without_grow():
    out = _run(0, 0)
    x, y = map(int, re.search(r"LOC (\d+) (\d+)", out).groups())
    assert 17840 <= x <= 22160 - 108 and "grow" not in out


@needs_tcl
def test_taken_window_grows_about_the_same_centre():
    out = _run(17000, 23000)                 # window x 17.84..22.16 fully taken; x2 window 15.68..24.32 has room
    assert "collector grow u_cland_collect_rst_rl_1/q (collector:rst_rl_1): window x2" in out, out
    x = int(re.search(r"LOC (\d+) (\d+)", out).group(1))
    assert 15680 <= x < 17000 or 23000 <= x <= 24320 - 108


@needs_tcl
def test_no_site_up_to_x8_still_fails_closed():
    out = _run(0, 40000)
    assert "ERR OT_CLAND no legal nonoverlapping row/site in reserved band for u_cland_collect_rst_rl_1/q" in out, out


def test_collectors_use_the_grow_path_and_skip_the_tiny_box_band_fit():
    loop = TCL[TCL.index("proc cland_put_collector"):]
    assert "if {!$coll} { cland_band_fit $prefix $rect $tag }" in loop
    assert "if {$coll} { cland_put_collector $i $rect $tag } else { cland_put $i $rect $tag }" in loop
