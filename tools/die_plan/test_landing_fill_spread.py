"""DIE-S81-66/CLS 11-05 (class CLAND-BAND, S81 dsdv_slice_c1x_C__t3 a3 sid_i0): a small ring in a large band whose fill
spread leaves one flop per row (an obstacle takes part of every row, so the free run holds one spread reservation)
shrinks its spread until the whole ring fits, instead of failing with 'no legal nonoverlapping row/site' while the band
is mostly empty."""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from test_landing_status_slide_resize import COMMON

TCL = Path(__file__).with_name("landing_placement.tcl").read_text()
pytestmark = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh unavailable")
NAMES = ["cland_group_insts", "cland_occupy", "cland_family_w", "cland_put_column", "cland_put", "cland_ffkey", "cland_freg_rekey", "cland_dsel_wch", "cland_wcc_w",
         "cland_column_select", "cland_kbit", "cland_nearest_bit", "cland_ctl_rekey", "cland_bus_pins", "cland_start_bterm_name",
         "cland_place_pinslot", "cland_place_pinslot_col", "cland_place_ff"]
OPT = ["cland_fill_spread"]
# band 3.0 x 5.4 um = 20 rows; an obstacle (reserved sites / strap) takes x 0..0.80 um of every row (free run 2.2 um)
RECT = "0 0 3.0 5.4"
OBST = "set cland_occ {}\nfor {set r 0} {$r < 20} {incr r} { dict set cland_occ $r [list [list 0 800]] }\n"


def _proc(name):
    m = re.search(r"^proc " + name + r" \{[^\n]*\} \{\n.*?\n\}\n|^proc " + name + r" \{[^\n]*\}\n", TCL, re.S | re.M)
    return m.group(0) if m else ""


def run(n, occ=OBST, env_extra=None, pins=None):
    s = COMMON + "\n" + "".join(_proc(x) for x in NAMES + OPT)
    s += "\nset cland_famw {};set cland_ff_fill 0.90;set instances {};set places {};set bterms {}\n" + occ
    for k in range(n):
        s += f"""proc i{k} {{m args}} {{
 switch $m {{getName {{return {{u_ring.c{k:03d}}}}} getMaster {{return DFFHQNx1_ASAP7_75t_R}}
 getPlacementStatus {{return PLACED}} setPlacementStatus {{}} setOrient {{}}
 setLocation {{dict set ::places {{u_ring.c{k:03d}}} $args}} }}
}}\nlappend instances i{k}\n"""
    for b, (px, py) in enumerate(pins or []):
        s += f"""proc bb{b} {{m args}} {{switch $m {{xMin {{return {px - 10}}} xMax {{return {px + 10}}} yMin {{return {py - 10}}} yMax {{return {py + 10}}}}}}}
proc bt{b} {{m args}} {{switch $m {{getName {{return {{i[{b}]}}}} getBBox {{return bb{b}}}}}}}\nlappend bterms bt{b}\n"""
    s += 'proc block {m args} {if {$m eq "getBTerms"} {return $::bterms};return $::instances}\nset ff_blk block\n'
    s += "if {[catch {cland_place_ff u_ring {%s} ring:i+ff} e]} {puts \"ERR $e\"} else {foreach {n p} $places {puts \"LOC $n $p\"}}\n" % RECT
    s = s.replace("getHeight { return 270 }", "getHeight { return 270 } isBlock { return 0 }")
    env = {k: v for k, v in os.environ.items() if k not in ("OT_CLAND_FIT_RESERVE", "OT_CLAND_PINSLOT", "OT_CLAND_SPREAD_FIT")}
    env["OT_CLAND_FIT_RESERVE"] = "1"          # as every S81 slice kit (config.mk)
    env.update(env_extra or {})
    cp = subprocess.run(["tclsh"], input=s, text=True, capture_output=True, env=env, check=True)
    assert not cp.stderr, cp.stderr
    return {nm: (int(x), int(y)) for nm, x, y in re.findall(r"LOC (\S+) (\d+) (\d+)", cp.stdout)}, cp.stdout


def _legal(placed):
    boxes = []
    for x, y in placed.values():
        assert x % 54 == 0 and y % 270 == 0 and 0 <= x and x + 162 <= 3000 and 0 <= y <= 5400 - 270
        assert x >= 800, (x, y)          # never on the obstacle
        box = (x, y, x + 162, y + 270)
        assert all(min(box[2], b[2]) <= max(box[0], b[0]) or min(box[3], b[3]) <= max(box[1], b[1]) for b in boxes)
        boxes.append(box)


def test_row_limited_small_ring_fits_at_a_smaller_spread():
    # 24 flops, 20 rows: the fill spread (0.9 x band / reserve = 5.2) reserves 2.16 um of the row per flop, the 2.2 um
    # free run holds one -> the 21st flop has no site (the old code fails with the band ~83 % empty)
    old, out_old = run(24, env_extra={"OT_CLAND_SPREAD_FIT": "0"})
    assert "ERR OT_CLAND no legal nonoverlapping row/site in reserved band for u_ring.c020" in out_old
    new, out = run(24)
    assert "ERR" not in out and len(new) == 24, out
    assert re.search(r"OT_CLAND fill spread ring:i\+ff: 24 flops do not fit at spread 5\.\d+ \(row-limited\), placed at [1-4]\.\d+", out)
    _legal(new)


def test_ring_that_fits_at_the_fill_spread_is_unchanged():
    # no obstacle: the same ring fits at its fill spread; placement identical to the dry-run-off code, no spread message
    old, out_old = run(24, occ="set cland_occ {}\n", env_extra={"OT_CLAND_SPREAD_FIT": "0"})
    new, out = run(24, occ="set cland_occ {}\n")
    assert old == new and len(new) == 24 and "fill spread" not in out


def test_band_too_small_at_any_spread_still_fails_closed():
    # at most 5 flops per row at spread 1.0 beside the obstacle: 150 flops cannot fit 20 rows -> same error as before, nothing moved
    _, out_old = run(150, env_extra={"OT_CLAND_SPREAD_FIT": "0"})
    _, out = run(150)
    assert "ERR OT_CLAND no legal nonoverlapping row/site in reserved band" in out
    assert out.splitlines()[-1].split(" (")[0] == out_old.splitlines()[-1].split(" (")[0]


def test_pinslot_old_fill_fallback_also_shrinks():
    # the S81 case: OT_CLAND_PINSLOT=1, a 2-bit bus whose pins are not a y column in key order (bit 1 pin below bit 0)
    # takes the old fill inside cland_place_pinslot; it shrinks the same way.  Unkeyed flops: names carry no bus bit,
    # so here the pinslot form has n=0 and takes the fallback as well.
    pins = [(3500, 2700), (3500, 2680)]
    old, out_old = run(24, env_extra={"OT_CLAND_SPREAD_FIT": "0", "OT_CLAND_PINSLOT": "1"}, pins=pins)
    assert "ERR OT_CLAND no legal" in out_old
    new, out = run(24, env_extra={"OT_CLAND_PINSLOT": "1"}, pins=pins)
    assert "ERR" not in out and len(new) == 24, out
    _legal(new)
