"""DIE-KV-33: opt-in OT_CLAND_FIT_RESERVE=1 - a CLAND cell site must be free of other occupancy over its whole reserved
footprint, so a FIRM cell upsized in place by timing-driven GPL cannot grow into a tapcell; default unchanged."""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TCL = (HERE / "landing_placement.tcl").read_text()

MOCK = r"""
set ff_x0 0; set ff_y0 0; set ff_x1 100000; set ff_y1 270; set ff_rh 270; set ff_sw 54; set ff_dbu 1000
set ff_orient [dict create 0 R0]; set cland_done {}; set cland_n 0; set cland_cursor {}
set cland_fh [open /dev/null w]
# one foreign obstacle (a tapcell) at sites 4..5 of row 0
set cland_occ [dict create 0 [list [list 216 324]]]
proc mst {m args} { switch $m { getWidth { return 162 } getHeight { return 270 } } }
set ::loc {}
proc ins {m args} {
  switch $m { getName { return u_cland_x/c } getMaster { return mst } getPlacementStatus { return PLACED }
    setPlacementStatus {} setOrient {} setLocation { set ::loc $args } }
}
cland_put ins {0 0 10 0.27} ring:x
puts "LOC $::loc"
"""


def _run(env):
    proc = re.search(r"proc cland_put \{i rect tag \{sp \{\}\} \{cur 0\}\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    out = subprocess.run(["tclsh"], input=proc + MOCK, capture_output=True, text=True, env=env, check=True).stdout
    return [int(v) for v in re.search(r"LOC (\S+) (\S+)", out).groups()]


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_default_body_fit_unchanged():
    env = {k: v for k, v in os.environ.items() if k != "OT_CLAND_FIT_RESERVE"}
    assert _run(env) == [0, 0]          # body 0..162 clears the tapcell at 216: placed at the band corner (old behaviour)


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_fit_reserve_skips_obstacle_inside_reserve():
    env = dict(os.environ, OT_CLAND_FIT_RESERVE="1")
    # reserve = ceil(162/0.4/54) * 54 = 432 would cover the tapcell at 216..324 -> next free site 324
    assert _run(env) == [324, 0]


def test_fit_reserve_is_opt_in():
    assert 'if {[info exists ::env(OT_CLAND_FIT_RESERVE)] && $::env(OT_CLAND_FIT_RESERVE) eq "1"}' in TCL
    assert "if {$x<$u && $x+$fw>$l}" in TCL and "set fw $w" in TCL


def test_gen_phys_emits_fit_reserve_only_on_plan_opt_in():
    """DIE-KV-34: gen phys exports OT_CLAND_FIT_RESERVE=1 only when the plan sets budgets.cland_fit_reserve
    (AUTOBUILD-PIPE-4 10-31 OWNER 12.27 b: otherwise the default is 'resize', see gen_phys._cland_fit_mode)."""
    import ast
    import sys
    src = (HERE / "gen_phys.py").read_text()
    line = '*([f"export OT_CLAND_FIT_RESERVE = {_cland_fit_mode(P.budgets)}"] if _cland_fit_mode(P.budgets) else []),'
    assert src.count(line) == 1
    ast.parse(src)
    sys.path.insert(0, str(HERE))
    import schema
    assert not schema.DEFAULT_BUDGETS.get("cland_fit_reserve")      # default: key absent -> kit config unchanged
