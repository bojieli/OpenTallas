"""FABLE-FIX-S81-SERDES 11-17: serdes_boot_release_local.tcl pulls a native sync tail DFF that a spread placement left
> 405 um from the fixed boot stage-2 site (S81 serdes__t13 H5, PLACE_DENSITY 0.30: 550.87 um) onto a macro-free site
<= 380 um away instead of failing the kit.  OpenDB is mocked in tclsh."""
import shutil
import subprocess
from pathlib import Path

import pytest

SRC = Path(__file__).with_name("serdes_boot_release_local.tcl")
needs_tcl = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")

MOCK = r"""
array set ::loc {%(LOC)s}
array set ::st {%(ST)s}
proc blk {op n} { return "inst:$n" }
proc unknown {cmd args} {
  if {[regexp {^inst:(.*)$} $cmd -> n]} {
    switch [lindex $args 0] {
      getLocation { return $::loc($n) } getPlacementStatus { return $::st($n) } getMaster { return mst }
      setLocation { set ::loc($n) [lrange $args 1 2]; return } setPlacementStatus { set ::st($n) [lindex $args 1]; return }
    }
  }
  if {$cmd eq "mst"} { switch [lindex $args 0] { getWidth { return 1080 } getHeight { return 270 } } }
  error "unknown $cmd $args"
}
source %(SRC)s
set rc [catch {ot_serdes_boot_tail_pull blk 1000.0 {%(TAILS)s} 1235.034 625.05 {%(MACS)s} {0 0 2885760 1226880}} res]
puts "RC=$rc RES=$res"
foreach n [lsort [array names ::loc]] { puts "LOC $n $::loc($n) $::st($n)" }
"""


def _run(loc, st, tails, macs=""):
    script = MOCK % dict(LOC=loc, ST=st, TAILS=tails, MACS=macs, SRC=SRC)
    return subprocess.run(["tclsh"], input=script, capture_output=True, text=True).stdout


def _span(out, name):
    x, y = [float(v) for v in next(ln for ln in out.splitlines() if ln.startswith(f"LOC {name} ")).split()[2:4]]
    return abs(x / 1000 - 1235.034) + abs(y / 1000 - 625.05)


@needs_tcl
def test_far_tail_is_pulled_to_380_and_near_tail_is_untouched():
    out = _run("a {1535034 875920} n {1335034 625050}", "a PLACED n PLACED", "{a 550.87} {n 100.0}")
    assert "RC=0" in out and "LOC n 1335034 625050 PLACED" in out, out
    assert 378.0 <= _span(out, "a") <= 381.0, out


@needs_tcl
def test_macro_on_the_first_site_takes_the_next_goal():
    # a macro box over the 380-um site: the pull settles on a nearer goal, never on the macro
    first = _run("a {1535034 875920}", "a PLACED", "{a 550.87}")
    x, y = [int(v) for v in next(ln for ln in first.splitlines() if ln.startswith("LOC a ")).split()[2:4]]
    out = _run("a {1535034 875920}", "a PLACED", "{a 550.87}", "{%d %d %d %d}" % (x - 2000, y - 2000, x + 3000, y + 2000))
    assert "RC=0" in out and _span(out, "a") <= 361.0, out


@needs_tcl
def test_fixed_tail_is_an_error():
    out = _run("a {1535034 875920}", "a FIRM", "{a 550.87}")
    assert "RC=1" in out and "cannot move" in out and "LOC a 1535034 875920 FIRM" in out, out
