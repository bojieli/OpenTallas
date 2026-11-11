"""DIE-QC-97 11-10: a writer-face (final START relay) window with no site grows like START/status cells (cland_put_face).

QC cbn_q01__clab6e67f2 a26 3_3 place: 'no legal nonoverlapping row/site in reserved band for
u_bound.u_cland_fstart_rsf_o/q$_SDFF_PN0_ (writer-face:rsf_o)'.  The window 232.768..241.408 x 0..8.64 keeps only the
16 core rows 4.32..8.64 (32 with the in-core slide); the a00 slot's stage-7 explicit ft bit sites (1.08-um DFFs on the
2.16-um grid) covered all of them, leaving 1.08-um gaps, and the relay flop reserves its resize-family width (1.188 um).
Runs the REAL cland_occupy / cland_put / cland_put_grow / cland_face_grows / cland_put_face procs (OpenDB mocked).
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

TCL = Path(__file__).with_name("landing_placement.tcl").read_text()
needs_tcl = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")


def _procs():
    occ = re.search(r"proc cland_occupy \{x y w h\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    put = re.search(r"proc cland_put \{i rect tag \{sp \{\}\} \{cur 0\}\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    grow = re.search(r"proc cland_put_grow \{i rect tag kind\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    fg = re.search(r"proc cland_face_grows \{\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    face = re.search(r"proc cland_put_face \{i rect tag\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    return occ + put + grow + fg + face


# core 4.32..400 x 4.32..100 um (dbu 1000), site 54, row 270.  Rows from y0 up to %(NR)d are packed with 1080-dbu
# station flops on the 2160-dbu grid (the face_flops.tcl lattice); the cell under test is 1080 wide and reserves
# 1188 (resize family), like DFFHQNx1 -> DFFHQNx3.
MOCK = r"""
set ff_x0 4320; set ff_y0 4320; set ff_x1 400000; set ff_y1 100000; set ff_rh 270; set ff_sw 54; set ff_dbu 1000
set ff_orient [dict create]; for {set r 0} {$r < 355} {incr r} { dict set ff_orient [expr {4320+$r*270}] R0 }
set cland_done {}; set cland_n 0; set cland_cursor {}; set cland_fh [open /dev/null w]
set cland_occ [dict create]
for {set r 0} {$r < %(NR)d} {incr r} {
  for {set x 4320} {$x < 400000} {incr x 2160} { cland_occupy $x [expr {4320+$r*270}] 1080 270 }
}
proc cland_family_w {m} { return 1188 }
set ::cland_pinslot_fit 1
set ::loc {}
proc m0 {op args} { switch $op { getWidth { return 1080 } getHeight { return 270 } isBlock { return 0 } getName { return DFFHQNx1 } } }
proc c0 {op args} { switch $op { getName { return u_bound.u_cland_fstart_s_o/q } getMaster { return m0 }
  getPlacementStatus { return PLACED } setLocation { set ::loc $args } default {} } }
if {[catch {cland_put_face c0 {232.768 0 241.408 8.64} writer-face:s_o} e]} { puts "ERR $e" } else { puts "LOC $::loc" }
"""


def _run(nrows, env=None):
    e = {k: v for k, v in os.environ.items() if k != "OT_CLAND_FACE_GROW"}
    e.update(env or {})
    out = subprocess.run(["tclsh"], input=_procs() + MOCK % dict(NR=nrows), capture_output=True, text=True, env=e)
    assert out.returncode == 0, out.stderr
    return out.stdout


def _loc(out):
    m = re.search(r"LOC (\d+) (\d+)", out)
    assert m, out
    return int(m.group(1)), int(m.group(2))


@needs_tcl
def test_window_rows_packed_but_its_core_slide_free_is_unchanged():
    out = _run(16)                                     # plain path (slide inside the core) still finds row 8.64
    assert "grow" not in out and _loc(out)[1] == 8640, out


@needs_tcl
def test_free_face_window_places_without_grow():
    out = _run(0)
    x, y = _loc(out)
    assert 232768 <= x <= 241408 - 1080 and 4320 <= y < 8640 and "grow" not in out, out


@needs_tcl
def test_lattice_over_all_window_rows_grows_to_the_first_free_row():
    # rows 4.32..12.96 packed: the window's own rows AND its slide inside the core (4.32..12.96) have no site, as in a26
    out = _run(32)
    assert "OT_CLAND face grow u_bound.u_cland_fstart_s_o/q (writer-face:s_o): window x2" in out, out
    x, y = _loc(out)
    assert y == 4320 + 32 * 270 and 228448 <= x <= 245728 - 1080, out


@needs_tcl
def test_lattice_beyond_x2_takes_a_larger_window():
    out = _run(70)                                     # packed to 23.22 um: x2 (slid to 4.32..21.6) has no row
    assert "window x4" in out, out
    assert _loc(out)[1] == 4320 + 70 * 270


@needs_tcl
def test_no_site_up_to_x32_still_fails_closed():
    out = _run(355)
    assert "ERR OT_CLAND no legal nonoverlapping row/site in reserved band for u_bound.u_cland_fstart_s_o/q" in out, out


@needs_tcl
def test_opt_out_restores_the_plain_path():
    out = _run(32, env={"OT_CLAND_FACE_GROW": "0"})
    assert "grow" not in out and "ERR OT_CLAND no legal" in out, out


def test_dispatch_routes_only_writer_face_tags_to_the_face_grow():
    assert ('elseif {$tag eq "local-reset"} { cland_put_grow $i $rect $tag local-reset } '
            'elseif {[string match {writer-face:*} $tag]} { cland_put_face $i $rect $tag } '
            'elseif {[string match {reader-start:*} $tag] || [string match {writer-start:*} $tag]} '
            '{ cland_put_start $i $rect $tag } else { cland_put $i $rect $tag }') in TCL


def test_band_bound_skips_writer_face_only_while_it_grows():
    # DIE-KV-97 up-front band bound: a writer-face band that takes the grow law is not bounded by its unscaled window
    assert ("if {[string match {writer-face:*} $tag] && [cland_face_grows]} return" in TCL)
