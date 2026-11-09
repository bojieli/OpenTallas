"""DIE-QC-97 11-09: a reader/writer START window with no site grows like status/collector cells (cland_put_start).

QC slw_stm_v1__cl05fc43f7__cl2086fa2c a11 (first band fail on a kit generated with 0b305f2395): the writer-start window
445.85..450.17 x 634.22..638.54 had rows and no macro, but FIRM ft-station flops (face_flops.tcl) covered it.  Runs the
REAL cland_occupy / cland_put / cland_put_grow / cland_put_start procs (OpenDB mocked), like test_landing_collector_grow.
"""
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
    start = re.search(r"proc cland_put_start \{i rect tag\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    return occ + put + grow + start


# 40 rows x 40000 dbu core (40 x 10.8 um), site 54, row 270
MOCK = r"""
set ff_x0 0; set ff_y0 0; set ff_x1 40000; set ff_y1 10800; set ff_rh 270; set ff_sw 54; set ff_dbu 1000
set ff_orient [dict create]; for {set r 0} {$r < 40} {incr r} { dict set ff_orient [expr {$r*270}] R0 }
set cland_done {}; set cland_n 0; set cland_cursor {}; set cland_fh [open /dev/null w]
set cland_occ [dict create]
for {set r 0} {$r < 40} {incr r} { dict lappend cland_occ $r [list %(OL)d %(OU)d] }
set ::loc {}
proc m0 {op args} { switch $op { getWidth { return 108 } getHeight { return 270 } isBlock { return 0 } getName { return DFFx1 } } }
proc c0 {op args} { switch $op { getName { return u_cland_writer_start_x_o_0/q } getMaster { return m0 }
  getPlacementStatus { return PLACED } setLocation { set ::loc $args } default {} } }
if {[catch {cland_put_start c0 {%(W)s} %(TAG)s} e]} { puts "ERR $e" } else { puts "LOC $::loc" }
"""

WIN = "17.84 3.24 22.16 7.56"


def _run(ol, ou, win=WIN, tag="writer-start:x_o", env=None):
    import os
    e = {k: v for k, v in os.environ.items() if k != "OT_CLAND_START_GROW"}
    e.update(env or {})
    out = subprocess.run(["tclsh"], input=_procs() + MOCK % dict(OL=ol, OU=ou, W=win, TAG=tag),
                         capture_output=True, text=True, env=e)
    assert out.returncode == 0, out.stderr
    return out.stdout


@needs_tcl
def test_free_window_places_inside_without_grow():
    out = _run(0, 0)
    x = int(re.search(r"LOC (\d+) (\d+)", out).group(1))
    assert 17840 <= x <= 22160 - 108 and "grow" not in out


@needs_tcl
def test_taken_window_grows_about_the_same_centre():
    out = _run(17000, 23000)
    assert "OT_CLAND start grow u_cland_writer_start_x_o_0/q (writer-start:x_o): window x2" in out, out
    x = int(re.search(r"LOC (\d+) (\d+)", out).group(1))
    assert 15680 <= x < 17000 or 23000 <= x <= 24320 - 108


@needs_tcl
def test_reader_start_takes_the_same_path():
    out = _run(17000, 23000, tag="reader-start:cws1_i")
    assert "OT_CLAND start grow" in out and "LOC" in out, out


@needs_tcl
def test_no_site_up_to_x32_still_fails_closed():
    out = _run(0, 100000)
    assert "ERR OT_CLAND no legal nonoverlapping row/site in reserved band for u_cland_writer_start_x_o_0/q" in out, out


@needs_tcl
def test_window_centred_outside_the_core_never_grows():
    out = _run(0, 0, win="60.0 3.24 64.32 7.56")       # centre x 62.16 um, core ends at 40 um
    assert "grow" not in out and "ERR OT_CLAND no legal" in out, out


@needs_tcl
def test_opt_out_restores_the_plain_path():
    out = _run(17000, 23000, env={"OT_CLAND_START_GROW": "0"})
    assert "grow" not in out and "ERR OT_CLAND no legal" in out, out


def test_dispatch_routes_only_start_tags_to_the_start_grow():
    assert ("elseif {[string match {reader-start:*} $tag] || [string match {writer-start:*} $tag]} "
            "{ cland_put_start $i $rect $tag } else { cland_put $i $rect $tag }") in TCL
    assert "if {$coll} { cland_put_collector $i $rect $tag } elseif {$tag eq \"local-reset\"}" in TCL
