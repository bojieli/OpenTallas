"""The optimized Tcl site enumeration keeps the original accepted coordinates and order."""
from pathlib import Path
import random
import subprocess


def test_actual_tcl_candidate_bounds_equal_full_gap_search():
    s = (Path(__file__).parent / "post_route_drv/hold_eco_internal_insert.tcl").read_text()
    start = s.index("        set pxlo ")
    end = s.index("\n        if {$b1 > $x}", start)
    # Exclude the busy-gap loop closing brace, retaining the actual candidate loop body.
    actual = s[start:end].rsplit("\n      }", 1)[0]
    baseline = """
for {set px [expr {$rx0 + (($x - $rx0 + $sw - 1) / $sw) * $sw}]} {$px + $mw <= $b0} {incr px $sw} {
 set d [expr {abs($px + $mw / 2 - $cx) + abs($ry - $cy)}]
 if {$d <= $rad} {lappend cands [list $d $px $ry $ror]}
}
"""
    rng = random.Random(1116)
    cases = []
    for _ in range(300):
        rx0 = rng.randrange(0, 100)
        sw = rng.randrange(1, 30)
        x = rx0 + rng.randrange(0, 80)
        b0 = x + rng.randrange(0, 4000)
        mw = rng.randrange(1, 100)
        cx = rng.randrange(rx0 - 500, b0 + 500)
        cy, ry, rad = rng.randrange(0, 100), rng.randrange(0, 100), rng.randrange(1, 300)
        cases.append((rx0, sw, x, b0, mw, cx, cy, ry, rad))
    script = "proc old {} {global rx0 sw x b0 mw cx cy ry rad ror;set cands {};" + baseline + ";return $cands}\n"
    script += "proc new {} {global rx0 sw x b0 mw cx cy ry rad ror;set cands {};" + actual + ";return $cands}\n"
    for case in cases:
        script += "lassign {" + " ".join(map(str, case)) + "} rx0 sw x b0 mw cx cy ry rad;set ror R0\n"
        script += "if {[old] ne [new]} {puts MISMATCH;exit 2}\n"
    script += "puts EQUIVALENT\n"
    r = subprocess.run(["tclsh"], input=script, text=True, capture_output=True)
    assert r.returncode == 0 and not r.stderr and "EQUIVALENT" in r.stdout, r.stdout + r.stderr
