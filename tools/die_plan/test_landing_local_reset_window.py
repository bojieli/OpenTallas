"""DQ87: a local reset copy with no site in its window takes the growing placement; other tags do not."""
import re
import subprocess
from pathlib import Path

SRC = (Path(__file__).resolve().parent / "landing_placement.tcl").read_text()


def _grow():
    m = re.search(r"^proc cland_put_grow .*?^}\n", SRC, re.S | re.M)
    assert m
    return m.group(0)


def _run(stub):
    tcl = _grow() + stub + r"""
proc I {args} {return x}
set i I
if {[catch {cland_put_grow $i {10 10 14.32 14.32} local-reset local-reset} e]} {puts "ERR $e"} else {puts OK}
"""
    return subprocess.run(["tclsh"], input=tcl, capture_output=True, text=True, check=True).stdout


def test_local_reset_tag_takes_growing_placement():
    assert "elseif {$tag eq \"local-reset\"} { cland_put_grow $i $rect $tag local-reset }" in SRC


def test_fits_first_window_unchanged():
    out = _run("proc cland_put {i r t} {puts \"R $r\"}\n")
    assert out.count("R ") == 1 and out.strip().endswith("OK") and "grow" not in out


def test_grows_nearest_first():
    out = _run("proc cland_put {i r t} {lassign $r a b c d; if {$c-$a < 15} {error \"OT_CLAND no legal x\"}; puts \"R $r\"}\n")
    assert "window x4" in out and out.count("R ") == 1 and out.strip().endswith("OK")


def test_full_everywhere_fails_closed():
    out = _run("proc cland_put {i r t} {error \"OT_CLAND no legal x\"}\n")
    assert out.startswith("ERR OT_CLAND no legal")


def test_other_error_is_not_swallowed():
    out = _run("proc cland_put {i r t} {error \"OT_CLAND duplicate placement x\"}\n")
    assert out.startswith("ERR OT_CLAND duplicate")
