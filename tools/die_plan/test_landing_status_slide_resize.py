"""FLOW-6 10-30 (HEAD hd_st_n3_turn / hd_turn_a v3, n3_turn v3nofr): two landing_placement.tcl cland_put fixes.

(1) A status window centred in the core margin can overlap the core by more than one cell height and still hold one
    row only (n3_turn d1_o: pin y 602.144, window 599.984..604.304, core top 600.48 -> row 600.21).  When that row has
    no fitting site the window slides, same size, inside the core and is scanned once more.  A window that places on
    the first scan is unchanged; a window that is not slide-eligible still fails closed.
(2) Opt-in OT_CLAND_FIT_RESERVE=resize: the site must be free over the widest drive variant of the cell's own family
    (DFFHQNx1 -> x2/x3), because timing-driven GPL resizes FIRM cells in place (n3_turn v3nofr 3_5 DPL-0033: FIRM ring
    DFFHQNx1 abutting a TAPCELL became DFFHQNx2, 54 dbu over it).  Unset and "=1" are unchanged.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TCL_PATH = Path(os.environ.get("OT_LANDING_PLACEMENT_TCL", HERE / "landing_placement.tcl"))
TCL = TCL_PATH.read_text()

pytestmark = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")


def _procs():
    put = re.search(r"proc cland_put \{i rect tag \{sp \{\}\} \{cur 0\}\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    fam = re.search(r"proc cland_family_w \{m\} \{\n.*?\n\}\n", TCL, re.S)
    occ = re.search(r"proc cland_occupy \{x y w h\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    return "set cland_famw {}\n" + occ + (fam.group(0) if fam else "") + put


# core 0..100 um x 0..5.4 um (20 rows of 0.27), dbu 1000; masters DFFHQNx1/x2/x3 widths 162/216/270 (scaled)
COMMON = r"""
set ff_x0 0; set ff_y0 0; set ff_x1 100000; set ff_y1 5400; set ff_rh 270; set ff_sw 54; set ff_dbu 1000
set ff_orient [dict create]; for {set r 0} {$r < 20} {incr r} { dict set ff_orient [expr {$r*270}] R0 }
set cland_done {}; set cland_n 0; set cland_cursor {}
set cland_fh [open /dev/null w]
foreach {nm w} {DFFHQNx1_ASAP7_75t_R 162 DFFHQNx2_ASAP7_75t_R 216 DFFHQNx3_ASAP7_75t_R 270 INVx1_ASAP7_75t_R 162} {
  proc $nm {m args} "switch \$m { getName { return $nm } getWidth { return $w } getHeight { return 270 } }"
}
proc mlib {m args} { return {DFFHQNx1_ASAP7_75t_R DFFHQNx2_ASAP7_75t_R DFFHQNx3_ASAP7_75t_R INVx1_ASAP7_75t_R} }
namespace eval ord { proc get_db {} { return mdb } }
proc mdb {m args} { return {mlib} }
set ::loc {}
proc ins {m args} {
  switch $m { getName { return u_cland_up_d1_o/fault_o } getMaster { return DFFHQNx1_ASAP7_75t_R }
    getPlacementStatus { return PLACED } setPlacementStatus {} setOrient {} setLocation { set ::loc $args } }
}
"""


def _run(body, env_extra=None):
    env = {k: v for k, v in os.environ.items() if k != "OT_CLAND_FIT_RESERVE"}
    env.update(env_extra or {})
    *setup, call = body.strip().splitlines()
    script = _procs() + COMMON + "\n".join(setup) + "\nif {[catch {" + call + "} e]} { puts \"ERR $e\" } else { puts \"LOC $::loc\" }\n"
    out = subprocess.run(["tclsh"], input=script, capture_output=True, text=True, env=env, check=True).stdout
    m = re.search(r"LOC (\S+) (\S+)", out)
    return [int(v) for v in m.groups()] if m else out.strip()


# status pin in the top core margin: window 5.0..9.32 um overlaps the core (top 5.4) by 0.4 um = one row (5.13)
STATUS = "cland_put ins {0 5.0 4.32 9.32} status:cland_up_fault_d1_o"


def test_margin_status_window_slides_when_its_single_row_is_full():
    body = "set cland_occ [dict create 19 [list [list 0 100000]]]\n" + STATUS
    # old code: ERR no legal site; new: same-size window slid to 1.08..5.40 um, first free row 1.08 (row 4)
    assert _run(body) == [0, 1080]


def test_margin_status_window_that_fits_is_unchanged():
    assert _run("set cland_occ [dict create]\n" + STATUS) == [0, 5130]          # edge row free: placed as before


def test_window_far_outside_core_still_fails_closed():
    out = _run("set cland_occ [dict create]\ncland_put ins {0 20.0 4.32 24.32} status:far")
    assert isinstance(out, str) and "OT_CLAND no legal nonoverlapping row/site" in out


# a TAPCELL at 162..270 on row 0: a DFFHQNx1 (162) body abuts it at x 0; its x3 variant (270) would cover it
RING = "set cland_occ [dict create 0 [list [list 162 270]]]\ncland_put ins {0 0 10 0.27} ring:x"


def test_resize_fit_clears_the_widest_family_variant():
    assert _run(RING, {"OT_CLAND_FIT_RESERVE": "resize"}) == [270, 0]


def test_resize_fit_default_and_reserve_one_unchanged():
    assert _run(RING) == [0, 0]                                                  # body fit (old behaviour)
    assert _run(RING, {"OT_CLAND_FIT_RESERVE": "1"}) == [270, 0]                 # reserve 432 from 0 covers 162: next 270


def test_gen_phys_fit_resize_is_default_on():
    # AUTOBUILD-PIPE-4 10-31 (OWNER 12.27 b): resize by default; reserve / explicit false are plan choices
    import sys
    sys.path.insert(0, str(HERE))
    import gen_phys
    src = (HERE / "gen_phys.py").read_text()
    assert src.count('export OT_CLAND_FIT_RESERVE = {_cland_fit_mode(P.budgets)}') == 1
    assert gen_phys._cland_fit_mode({}) == "resize" and gen_phys._cland_fit_resize({}) is True
    assert gen_phys._cland_fit_mode({"cland_fit_reserve": True}) == "1"
    assert gen_phys._cland_fit_mode({"cland_fit_resize": False}) is None
    with pytest.raises(SystemExit):
        gen_phys._cland_fit_resize({"cland_fit_resize": True, "cland_fit_reserve": True})