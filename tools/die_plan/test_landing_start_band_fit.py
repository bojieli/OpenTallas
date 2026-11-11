"""DIE-KV-97 11-10 (KV kv3_pv_v1 / v1n / v6n place FAIL "writer-start ... band upper bound 0.0 um2, checked before
placement"): the up-front band bound (FLOW-KITFAIL-3) must not fail a START / local-reset band whose cells take the
grow law (cland_put_start / cland_put_grow); rings and START windows without grow keep the bound."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TCL = (HERE / "landing_placement.tcl").read_text()
needs_tcl = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")


def _proc(name, args):
    return re.search(r"proc " + name + r" \{" + re.escape(args) + r"\} \{\n.*?\n\}\n", TCL, re.S).group(0)


# 4 rows x 2000 dbu core; every row fully occupied (FIRM station flops), 3 cells of width 108 to land
MOCK = r"""
set ff_x0 0; set ff_y0 0; set ff_x1 2000; set ff_y1 1080; set ff_rh 270; set ff_sw 54; set ff_dbu 1000
set ff_orient [dict create 0 R0 270 MX 540 R0 810 MX]; set cland_done {}
set cland_occ [dict create 0 {{0 2000}} 1 {{0 2000}} 2 {{0 2000}} 3 {{0 2000}}]
%(ENV)s
proc mst {op args} { switch $op { getWidth { return 108 } getHeight { return 270 } isBlock { return 0 } } }
proc ins {k op args} { switch $op { getName { return u_cland_g/c$k } getMaster { return mst } } }
set insts {}
for {set k 0} {$k < 3} {incr k} { interp alias {} i$k {} ins $k; lappend insts i$k }
proc cland_group_insts {prefix} { return $::insts }
set fit [catch {cland_band_fit u_cland_g {0.2 0.0 1.8 1.08} %(TAG)s} fe]
puts "FIT $fit"
"""


def _fit(tag, env=""):
    body = _proc("cland_start_grows", "rect") + _proc("cland_band_fit", "prefix rect tag") + MOCK % dict(TAG=tag, ENV=env)
    out = subprocess.run(["tclsh"], input=body, capture_output=True, text=True, check=True).stdout
    return int(re.search(r"FIT (\d)", out).group(1))


@needs_tcl
def test_full_start_window_is_left_to_the_grow():
    assert _fit("writer-start:ft7_o") == 0
    assert _fit("reader-start:ft7_i") == 0
    assert _fit("local-reset") == 0


@needs_tcl
def test_ring_band_keeps_the_bound():
    assert _fit("ring:ft7_o") == 1


@needs_tcl
def test_start_without_grow_keeps_the_bound():
    assert _fit("writer-start:ft7_o", "set ::env(OT_CLAND_START_GROW) 0") == 1


@needs_tcl
def test_literal_reset_skips_only_with_land_reserve():
    assert _fit("literal-local-reset") == 1
    assert _fit("literal-local-reset", "set ::env(OT_LAND_RESERVE) 1") == 0
