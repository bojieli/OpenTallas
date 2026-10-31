"""FLOW-11 10-30 (DIE-HEAD-43 (C)): opt-in OT_CLAND_PINSLOT=1 fits ring slot flops next to their own bus-bit pin."""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import gen_phys
from test_landing_status_slide_resize import COMMON

TCL = Path(__file__).with_name("landing_placement.tcl").read_text()
pytestmark = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh unavailable")
NAMES = ["cland_occupy", "cland_family_w", "cland_put_column", "cland_put", "cland_ffkey", "cland_dsel_wch",
         "cland_column_select", "cland_kbit", "cland_nearest_bit", "cland_ctl_rekey", "cland_bus_pins",
         "cland_place_pinslot", "cland_place_ff"]
BITS, SLOTS = 8, 2
PIN_Y = {b: 300 + 650 * b for b in range(BITS)}     # W-face pins i[b] at x 0, y 0.30 .. 4.85 um


def _proc(name):
    return re.search(r"^proc " + name + r" \{[^\n]*\} \{\n.*?\n\}\n|^proc " + name + r" \{[^\n]*\}\n", TCL, re.S | re.M).group(0)


def run(pinslot, tag="ring:i+ff", pin_y=PIN_Y):
    s = COMMON + "\n" + "".join(_proc(n) for n in NAMES)
    s += "\nset cland_occ {};set cland_famw {};set cland_ff_fill 0.10;set instances {};set places {};set bterms {}\n"
    for bit in range(BITS):
        for slot in range(SLOTS):
            inst, name = f"i{bit}{slot}", f"u_ring.s_d[{slot}][{bit}]"
            s += f"""proc {inst} {{m args}} {{
 switch $m {{getName {{return {{{name}}}}} getMaster {{return DFFHQNx1_ASAP7_75t_R}}
 getPlacementStatus {{return PLACED}} setPlacementStatus {{}} setOrient {{}}
 setLocation {{dict set ::places {{{name}}} $args}} }}
}}\nlappend instances {inst}\n"""
        y = pin_y[bit]
        s += f"""proc bb{bit} {{m args}} {{switch $m {{xMin {{return 0}} xMax {{return 20}} yMin {{return {y - 10}}} yMax {{return {y + 10}}}}}}}
proc bt{bit} {{m args}} {{switch $m {{getName {{return {{i[{bit}]}}}} getBBox {{return bb{bit}}}}}}}\nlappend bterms bt{bit}\n"""
    s += 'proc block {m args} {if {$m eq "getBTerms"} {return $::bterms};return $::instances}\nset ff_blk block\n'
    s += "if {[catch {cland_place_ff u_ring {2 0 12 5.4} %s} e]} {puts \"ERR $e\"} else {foreach {n p} $places {puts \"LOC $n $p\"}}\n" % tag
    s = s.replace("getHeight { return 270 }", "getHeight { return 270 } isBlock { return 0 }")
    env = {k: v for k, v in os.environ.items() if k not in ("OT_CLAND_FIT_RESERVE", "OT_CLAND_PINSLOT")}
    if pinslot is not None:
        env["OT_CLAND_PINSLOT"] = pinslot
    cp = subprocess.run(["tclsh"], input=s, text=True, capture_output=True, env=env, check=True)
    assert not cp.stderr and "ERR" not in cp.stdout, cp.stdout + cp.stderr
    return {n: (int(x), int(y)) for n, x, y in re.findall(r"LOC (\S+) (\d+) (\d+)", cp.stdout)}, cp.stdout


def farthest(placed, pin_y=PIN_Y):
    # pin_reg judges a declared ring pin at its FARTHEST slot flop (geom_rules.land_ring_captures)
    return {b: max(x + 81 + abs(y + 135 - pin_y[b]) for n, (x, y) in placed.items() if n.endswith(f"[{b}]"))
            for b in range(BITS)}


def test_unset_or_zero_is_the_old_bit_major_fill():
    old, _ = run(None)
    zero, _ = run("0")
    assert old == zero and len(old) == BITS * SLOTS
    # bit-major from the band low corner: the high bits sit far below their pins
    assert max(farthest(old).values()) > 4000


def test_pinslot_fits_every_slot_next_to_its_own_pin_without_overlap():
    old, _ = run(None)
    new, out = run("1")
    assert len(new) == BITS * SLOTS and f"OT_CLAND pinslot u_ring: {BITS * SLOTS} ring flops next to their i bit pin (stretched over pin y 0.30..4.85, spread " in out
    boxes = []
    for x, y in new.values():
        assert x % 54 == 0 and y % 270 == 0 and 2000 <= x and x + 162 <= 12000 and 0 <= y <= 5400 - 270
        box = (x, y, x + 162, y + 270)
        assert all(min(box[2], b[2]) <= max(box[0], b[0]) or min(box[3], b[3]) <= max(box[1], b[1]) for b in boxes)
        boxes.append(box)
    for n, (x, y) in new.items():
        bit = int(re.search(r"\]\[(\d+)\]$", n).group(1))
        assert abs(y + 135 - PIN_Y[bit]) <= 1000, (n, y)
    assert max(farthest(new).values()) < max(farthest(old).values()) / 2


def test_lsb_high_bus_is_stretched_in_its_key_order():
    # lsb_high pins (bit 0 at the top) with the plan's +ffr tag: keys run from the highest bit = lowest pin
    desc = {b: PIN_Y[BITS - 1 - b] for b in range(BITS)}
    new, out = run("1", tag="ring:i+ffr", pin_y=desc)
    old, _ = run(None, tag="ring:i+ffr", pin_y=desc)
    assert "stretched over pin y 0.30..4.85" in out
    assert max(farthest(new, desc).values()) < max(farthest(old, desc).values()) / 2


def test_pins_against_the_key_order_keep_the_old_fill():
    # +ffr on lsb-low pins: the y order runs against the keys -> no stretch, exactly the old placement
    new, out = run("1", tag="ring:i+ffr")
    old, _ = run(None, tag="ring:i+ffr")
    assert new == old and "pins not a y column in key order: old fill" in out


def test_column_form_is_not_switched():
    assert "} elseif {[info exists ::env(OT_CLAND_PINSLOT)]" in TCL
    i = TCL.index("if {[string match {ring:*+x+ff*} $tag]} {\n  set cland_col_reduce")
    assert i < TCL.index("} elseif {[info exists ::env(OT_CLAND_PINSLOT)]")


def test_gen_phys_exports_only_for_named_types():
    b = dict(cland_pinslot_types=["hd_turn_a", "slice_station"])
    assert gen_phys._cland_pinslot(b, "hd_turn_a") and gen_phys._cland_pinslot(b, "slice_station__t3")
    assert not gen_phys._cland_pinslot(b, "hd_turn_b") and not gen_phys._cland_pinslot({}, "hd_turn_a")
