"""FLOW-KITFAIL-3 (S81-KITS-B iqf__t1): an all-cells landing ring whose reserved footprints cannot fit its band fails
with the same "no legal nonoverlapping row/site" error BEFORE the O(n^2) first-fit cland_put loop, never on a band the
first fit would fill (sound upper bound), and leaves fitting bands unchanged."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TCL = (HERE / "landing_placement.tcl").read_text()
needs_tcl = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")


def _procs():
    put = re.search(r"proc cland_put \{i rect tag \{sp \{\}\} \{cur 0\}\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    occ = re.search(r"proc cland_occupy \{x y w h\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    fit = re.search(r"proc cland_band_fit \{prefix rect tag\} \{\n.*?\n\}\n", TCL, re.S)
    return occ + put + (fit.group(0) if fit else "proc cland_band_fit {args} {}\n")


# 4 rows x 2000 dbu core, site 54, row 270; cells u_cland_g/c<k> of width W[k]; foreign occupancy from OBST
MOCK = r"""
set ff_x0 0; set ff_y0 0; set ff_x1 %(X1)d; set ff_y1 1080; set ff_rh 270; set ff_sw 54; set ff_dbu 1000
set ff_orient [dict create 0 R0 270 MX 540 R0 810 MX]; set cland_done {}; set cland_n 0; set cland_cursor {}
set cland_fh [open /dev/null w]
set cland_occ [dict create]
foreach o {%(OBST)s} { lassign $o r l u; dict lappend cland_occ $r [list $l $u] }
set ::W {%(W)s}
proc mst {k op args} { switch $op { getWidth { return [lindex $::W $k] } getHeight { return 270 } isBlock { return 0 } getName { return BUFx2 } } }
proc ins {k op args} { switch $op { getName { return u_cland_g/c$k } getMaster { return m$k } getPlacementStatus { return PLACED } default {} } }
proc mk {k} { interp alias {} m$k {} mst $k; interp alias {} i$k {} ins $k; return i$k }
set insts {}
for {set k 0} {$k < [llength $::W]} {incr k} { lappend insts [mk $k] }
proc blk {op args} { return $::insts }
set ff_blk blk
set fit [catch {cland_band_fit u_cland_g {0 0 %(BX)s 1.08} ring:g} fe]
set n 0
set put [catch { foreach i $insts { cland_put $i {0 0 %(BX)s 1.08} ring:g; incr n } } pe]
puts "FIT $fit PUT $put N $n"
"""


def _run(W, obst=(), bx=2.0, x1=2000):
    body = _procs() + MOCK % dict(X1=x1, OBST=" ".join("{%d %d %d}" % o for o in obst), W=" ".join(map(str, W)),
                                  BX=bx)
    out = subprocess.run(["tclsh"], input=body, capture_output=True, text=True, check=True).stdout
    f, p, n = re.search(r"FIT (\d) PUT (\d) N (\d+)", out).groups()
    return int(f), int(p), int(n)


@needs_tcl
def test_overfull_band_fails_before_placement():
    # 4 rows x 2000 dbu; each 108-wide cell reserves ceil(108/0.4/54)*54 = 270 -> 7 per row + overhang; 60 cells cannot fit
    fit, put, n = _run([108] * 60)
    assert fit == 1 and put == 1          # the first fit fails too (the bound is not stricter than placement)


@needs_tcl
def test_fitting_band_passes_and_places_all():
    fit, put, n = _run([108] * 20, obst=[(0, 500, 600), (2, 1000, 1100)])
    assert (fit, put, n) == (0, 0, 20)


@needs_tcl
def test_bound_never_rejects_a_band_first_fit_fills():
    import random
    rnd = random.Random(7)
    seen_tight = 0
    for _ in range(150):
        W = [rnd.choice([54, 108, 162, 216, 324]) for _ in range(rnd.randint(5, 45))]
        obst = []
        for r in range(4):
            for _ in range(rnd.randint(0, 3)):
                l = rnd.randrange(0, 1900, 54); obst.append((r, l, l + rnd.choice([54, 108, 216])))
        fit, put, n = _run(W, obst)
        assert not (fit == 1 and put == 0), (W, obst)   # never fails early where first fit succeeds
        seen_tight += (put == 1)
    assert seen_tight > 10                               # the sample includes infeasible bands


def test_all_cells_branch_checks_before_first_fit():
    i = TCL.index("cland_band_fit $prefix $rect $tag\n foreach i [$ff_blk getInsts]")
    assert TCL.index("proc cland_band_fit") < i
    # the ring_place=ff branch and cland_put itself are untouched
    assert "if {$x<$u && $x+$fw>$l} { set skip [expr {max($skip,$u)}] }" in TCL
