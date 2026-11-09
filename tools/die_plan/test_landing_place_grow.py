"""DIE-QC-97 11-09: a full single non-ring landing window (start/status/local-reset) grows x3/x5/x7 around its centre.

QC slw_stm_v1__cl05fc43f7__cl2086fa2c a11 (first band fail on a kit generated with 0b305f2395): writer-start window
445.85..450.17 x 634.22..638.54 had rows and no macro, but FIRM ft-station flops (face_flops.tcl) covered it.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TCL = (HERE / "landing_placement.tcl").read_text()


def _proc(name):
    return re.search(r"^proc %s \{.*?\n\}\n" % re.escape(name), TCL, re.S | re.M).group(0)


HARNESS = r"""
set ff_dbu 1000; set ff_x0 0; set ff_y0 0; set ff_x1 100000; set ff_y1 100000; set ff_rh 270; set ff_sw 54
set ff_orient {}; for {set y 0} {$y < 100000} {incr y 270} { dict set ff_orient $y R0 }
set cland_occ {}; set cland_done {}; set cland_n 0; set cland_cursor {}
set cland_fh [open /dev/null w]
proc mk {name} {
  set ::loc($name) {}; set ::st($name) PLACED
  proc $name {args} [string map [list @N@ $name] {
    switch -- [lindex $args 0] {
      getName { return @N@ }
      getMaster { return mst }
      getPlacementStatus { return $::st(@N@) }
      setPlacementStatus { set ::st(@N@) [lindex $args 1] }
      setOrient { }
      setLocation { set ::loc(@N@) [lrange $args 1 2] }
    }
  }]
}
proc mst {args} { switch -- [lindex $args 0] { getWidth { return 270 } getHeight { return 270 } getName { return DFFHQNx1 } } }
"""


def _run(body, env=None):
    import os
    e = dict(os.environ)
    e.pop("OT_CLAND_GROW", None)
    if env:
        e.update(env)
    # tclsh reading a script from stdin exits 0 after an error, so the body runs under catch with an explicit status
    src = _proc("cland_occupy") + _proc("cland_put") + HARNESS + "if {[catch {\n" + body + "} e]} { puts stderr $e; exit 3 }\n"
    return subprocess.run(["tclsh"], input=src, capture_output=True, text=True, env=e)


WIN = "{10.0 10.0 14.32 14.32}"
FILL_BASE = "cland_occupy 9000 9720 6000 4860\n"          # covers every row/site of the base window


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_free_window_is_unchanged():
    r = _run("mk a\ncland_put a %s writer-start:x\nputs LOC=$::loc(a)\n" % WIN)
    assert r.returncode == 0, r.stderr
    assert "LOC=10044 10260" in r.stdout and "OT_CLAND grow" not in r.stdout


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_full_window_grows_x3_and_places_near():
    r = _run(FILL_BASE + "mk a\ncland_put a %s writer-start:x\nputs LOC=$::loc(a)\n" % WIN)
    assert r.returncode == 0, r.stderr
    assert "OT_CLAND grow writer-start:x: a placed in window x3" in r.stdout
    x, y = (int(v) for v in re.search(r"LOC=(\d+) (\d+)", r.stdout).groups())
    assert 5680 <= x <= 18640 - 270 and 5680 <= y <= 18640 - 270          # inside the x3 window
    assert not (9000 <= x < 15000 and 9720 <= y < 14580)                 # not on the occupied block


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_opt_out_and_ring_tags_fail_closed():
    r = _run(FILL_BASE + "mk a\ncland_put a %s writer-start:x\n" % WIN, {"OT_CLAND_GROW": "0"})
    assert r.returncode != 0 and "OT_CLAND no legal nonoverlapping" in r.stderr
    r = _run(FILL_BASE + "mk a\ncland_put a %s ring:x\n" % WIN)
    assert r.returncode != 0 and "OT_CLAND no legal nonoverlapping" in r.stderr and "grow" not in r.stdout


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_x7_full_still_fails_closed():
    r = _run("cland_occupy 0 0 50000 50000\nmk a\ncland_put a %s local-reset\n" % WIN)
    assert r.returncode != 0 and "OT_CLAND no legal nonoverlapping row/site in reserved band for a (local-reset)" in r.stderr


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_dry_probe_does_not_grow():
    r = _run(FILL_BASE + "set ::cland_fill_dry 1\nmk a\ncland_put a %s writer-start:x\n" % WIN)
    assert r.returncode != 0 and "grow" not in r.stdout
