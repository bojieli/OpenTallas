"""AUTOBUILD-PIPE-2 10-31 (S81 slice_station wave: every place FAIL was 'no legal ... (collector:rst_rl_N)'): a reset
collector cell without a site in its relay window (+-2.16 um; several relays on one xy, or the relay inside a ring
band the FIRM ring fill took) takes the window grown about the same centre x2/x4/x8/x16/x32; with no site even there it fails
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
    grow = re.search(r"proc cland_put_grow \{i rect tag kind\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    coll = re.search(r"proc cland_put_collector \{i rect tag\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    return occ + put + grow + coll


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
def test_no_site_up_to_x32_still_fails_closed():
    out = _run(0, 100000)
    assert "ERR OT_CLAND no legal nonoverlapping row/site in reserved band for u_cland_collect_rst_rl_1/q" in out, out


@needs_tcl
def test_window_grows_to_x16_about_the_same_centre():
    out = _run(0, 38000)                     # x8 window 2.72..37.28 fully taken; x16 reaches 38..40 (QC slw_hc1 11-05)
    assert "collector grow u_cland_collect_rst_rl_1/q (collector:rst_rl_1): window x16" in out, out


def test_collectors_use_the_grow_path_and_skip_the_tiny_box_band_fit():
    loop = TCL[TCL.index("proc cland_put_collector"):]
    assert "if {!$coll} { cland_band_fit $prefix $rect $tag }" in loop
    assert "if {$coll} { cland_put_collector $i $rect $tag } " in loop


# KIT-TRIAGE-1/G4 11-01 (KV kv3_io_cor@4 'no legal ... (status:landing_ready_ft10_i)'): status stages take the same
# grow path as collectors
STATUS = MOCK.replace("cland_put_collector c0 {17.84 3.24 22.16 7.56} collector:rst_rl_1",
                      "cland_put_grow c0 {17.84 3.24 22.16 7.56} status:landing_ready_ft10_i status")


@needs_tcl
def test_status_window_taken_grows():
    out = subprocess.run(["tclsh"], input=_procs() + STATUS % dict(OL=17000, OU=23000), capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert "OT_CLAND status grow u_cland_collect_rst_rl_1/q (status:landing_ready_ft10_i): window x2" in out.stdout, out.stdout
    out = subprocess.run(["tclsh"], input=_procs() + STATUS % dict(OL=0, OU=100000), capture_output=True, text=True)
    assert "ERR OT_CLAND no legal nonoverlapping row/site in reserved band" in out.stdout, out.stdout


def test_status_loop_uses_the_grow_path_defined_before_it():
    assert TCL.index("proc cland_put_grow") < TCL.index("foreach spec $cland_status")
    loop = TCL[TCL.index("foreach spec $cland_status"):TCL.index("foreach spec $cland_optional_groups")]
    assert "cland_put_grow [lindex $drivers 0] $cland_sw status:$net status" in loop
    assert "} else { cland_put [lindex $drivers 0] $cland_sw status:$net }" in loop


def test_status_pin_in_the_core_margin_takes_the_grow_path():
    """DIE-S81-53/BAND (S81 leaf t56 landing_ready_ft9_i): pin y 0, core y 4.32: the +-2.16 um window misses the core but
    the grown one reaches it, so a crowded slid window grows.  Only a point beyond the largest grown window stays plain."""
    loop = TCL[TCL.index("foreach spec $cland_status"):TCL.index("foreach spec $cland_optional_groups")]
    cond = re.search(r"if \{(\(\$x\+17\.28\).*?)\} \{\n  cland_put_grow", loop, re.S).group(1)
    assert "($y-17.28)*$ff_dbu < $ff_y1" in cond and "cland_sw 3" not in cond


def test_optional_group_cells_take_the_grow_path():
    """DIE-QC-73 11-05: raw-copy-optional cells (reset copies) grow like collectors, no plain cland_put."""
    body = TCL.split("foreach spec $cland_optional_groups {", 1)[1].split("\n}\n", 1)[0]
    assert "cland_put_grow $i $rect $tag raw-copy" in body
    assert "\n  cland_put $i" not in body


FOLLOW = r"""
rename file _file
proc file {op args} { if {$op eq "exists" && [lindex $args 0] eq "/work/macro_moves.json"} { return %(MOVES)d }; return [_file $op {*}$args] }
%(RTR)s
"""


def _run_follow(moves, rtr, ol=0, ou=40000):
    # every row fully taken, so the plan window cannot reach a site at any grow
    mock = MOCK % dict(OL=ol, OU=ou)
    head = FOLLOW % dict(MOVES=moves, RTR=rtr)
    out = subprocess.run(["tclsh"], input=_procs() + head + mock, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return out.stdout


@needs_tcl
def test_no_macro_moves_fails_closed_as_before():
    out = _run_follow(0, "set ::rtr_at [dict create rst_rl_1 {20000 5400}]")
    assert "ERR OT_CLAND no legal" in out and "follows relay" not in out


@needs_tcl
def test_macro_moves_without_a_relay_fails_closed():
    out = _run_follow(1, "set ::rtr_at [dict create rst_rl_9 {20000 5400}]")
    assert "ERR OT_CLAND no legal" in out and "follows relay" not in out


@needs_tcl
def test_macro_moves_with_relay_also_blocked_fails_closed():
    out = _run_follow(1, "set ::rtr_at [dict create rst_rl_1 {20000 5400}]")
    assert "follows relay" in out and "ERR OT_CLAND no legal" in out


@needs_tcl
def test_macro_moves_follows_the_placed_relay():
    # core 0..200 um, occupancy 0..150 um in every row: plan window at x=20 um reaches 89 um at x32, so no site; relay at x=155
    mock = (MOCK % dict(OL=0, OU=150000)).replace("set ff_x1 40000", "set ff_x1 200000")
    head = FOLLOW % dict(MOVES=1, RTR="set ::rtr_at [dict create rst_rl_1 {155000 5400}]")
    out = subprocess.run(["tclsh"], input=_procs() + head + mock, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    out = out.stdout
    assert "follows relay" in out, out
    x = int(re.search(r"LOC (\d+) (\d+)", out).group(1))
    assert 150000 <= x <= 160000


@needs_tcl
def test_macro_moves_window_that_fits_ignores_the_relay():
    mock = MOCK % dict(OL=0, OU=0)
    head = FOLLOW % dict(MOVES=1, RTR="set ::rtr_at [dict create rst_rl_1 {35000 5400}]")
    out = subprocess.run(["tclsh"], input=_procs() + head + mock, capture_output=True, text=True).stdout
    assert "follows relay" not in out
    x = int(re.search(r"LOC (\d+) (\d+)", out).group(1))
    assert 17840 <= x <= 22160 - 108
