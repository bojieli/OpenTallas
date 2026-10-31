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
         "cland_place_pinslot", "cland_place_pinslot_col", "cland_place_ff"]
BITS, SLOTS = 8, 2
PIN_Y = {b: 300 + 650 * b for b in range(BITS)}     # W-face pins i[b] at x 0, y 0.30 .. 4.85 um


def _proc(name):
    return re.search(r"^proc " + name + r" \{[^\n]*\} \{\n.*?\n\}\n|^proc " + name + r" \{[^\n]*\}\n", TCL, re.S | re.M).group(0)


def run(pinslot, tag="ring:i+ff", pin_y=PIN_Y, pin_xy=None, rect="2 0 12 5.4", occ=""):
    s = COMMON + "\n" + "".join(_proc(n) for n in NAMES)
    s += "\nset cland_occ {};set cland_famw {};set cland_ff_fill 0.10;set instances {};set places {};set bterms {}\n" + occ
    for bit in range(BITS):
        for slot in range(SLOTS):
            inst, name = f"i{bit}{slot}", f"u_ring.s_d[{slot}][{bit}]"
            s += f"""proc {inst} {{m args}} {{
 switch $m {{getName {{return {{{name}}}}} getMaster {{return DFFHQNx1_ASAP7_75t_R}}
 getPlacementStatus {{return PLACED}} setPlacementStatus {{}} setOrient {{}}
 setLocation {{dict set ::places {{{name}}} $args}} }}
}}\nlappend instances {inst}\n"""
        px, y = (pin_xy[bit] if pin_xy else (10, pin_y[bit]))
        s += f"""proc bb{bit} {{m args}} {{switch $m {{xMin {{return {px - 10}}} xMax {{return {px + 10}}} yMin {{return {y - 10}}} yMax {{return {y + 10}}}}}}}
proc bt{bit} {{m args}} {{switch $m {{getName {{return {{i[{bit}]}}}} getBBox {{return bb{bit}}}}}}}\nlappend bterms bt{bit}\n"""
    s += 'proc block {m args} {if {$m eq "getBTerms"} {return $::bterms};return $::instances}\nset ff_blk block\n'
    s += "if {[catch {cland_place_ff u_ring {%s} %s} e]} {puts \"ERR $e\"} else {foreach {n p} $places {puts \"LOC $n $p\"}}\n" % (rect, tag)
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


def test_column_form_keeps_its_fill_unless_pins_run_along_x():
    # the +x branch still comes before the y-column pinslot branch; a +x band only changes for an x row of pins
    i = TCL.index(" } elseif {[string match {ring:*+x+ff*} $tag]} {\n  set cland_col_reduce")
    assert i < TCL.index("} elseif {[info exists ::env(OT_CLAND_PINSLOT)]")
    old, _ = run(None, tag="ring:i@2.0+x+ff")
    new, out = run("1", tag="ring:i@2.0+x+ff")      # W-face pins = a y column: not an x row
    assert new == old and "pins not an x row in key order: old column fill" in out


# FLOW-12 10-30 (HEAD turn_b): +x column band, bus pins along x on the N (or S) face beyond the band edge
NPIN = {b: (2500 + 1250 * b, 5500) for b in range(BITS)}     # N face above the band top 5.4 um, x 2.5 .. 11.25 um
SPIN = {b: (2500 + 1250 * b, -100) for b in range(BITS)}     # S face below the band bottom 0


def farthest_xy(placed, pins):
    return {b: max(abs(x + 81 - pins[b][0]) + abs(y + 135 - pins[b][1]) for n, (x, y) in placed.items()
                   if n.endswith(f"[{b}]")) for b in range(BITS)}


def _no_overlap(placed):
    boxes = []
    for x, y in placed.values():
        assert x % 54 == 0 and y % 270 == 0 and 2000 <= x and x + 162 <= 12000 and 0 <= y <= 5400 - 270
        box = (x, y, x + 162, y + 270)
        assert all(min(box[2], b[2]) <= max(box[0], b[0]) or min(box[3], b[3]) <= max(box[1], b[1]) for b in boxes)
        boxes.append(box)


@pytest.mark.parametrize("pins,face", [(NPIN, "N"), (SPIN, "S")])
def test_x_row_pins_pack_the_column_band_on_their_face(pins, face):
    tag = "ring:i@2.0+x+ff"
    old, _ = run(None, tag=tag, pin_xy=pins)
    new, out = run("1", tag=tag, pin_xy=pins)
    assert len(new) == BITS * SLOTS
    assert f"OT_CLAND pinslot u_ring: {BITS * SLOTS} ring flops next to their i bit pin ({face} face strip " in out
    assert "0 by the whole band" in out
    _no_overlap(new)
    ys = [y for x, y in new.values()]
    # the whole ring sits in the strip on the pin face (rows next to the face edge)
    assert (min(ys) >= 5400 - 270 * 6) if face == "N" else (max(ys) <= 270 * 5)
    # each bit's slots sit in the columns under its own pin, in pin order
    for n, (x, y) in new.items():
        bit = int(re.search(r"\]\[(\d+)\]$", n).group(1))
        assert abs(x + 81 - pins[bit][0]) <= 1500, (n, x)
    assert max(farthest_xy(new, pins).values()) < max(farthest_xy(old, pins).values()) / 2


def test_x_row_against_the_key_order_keeps_the_old_column_fill():
    desc = {b: NPIN[BITS - 1 - b] for b in range(BITS)}         # x falls with the key: no stretch, old fill
    old, _ = run(None, tag="ring:i@2.0+x+ff", pin_xy=desc)
    new, out = run("1", tag="ring:i@2.0+x+ff", pin_xy=desc)
    assert new == old and "pins not an x row in key order: old column fill" in out
    # the plan's +ffr on that face reverses the keys: then the row follows them and is packed
    new, out = run("1", tag="ring:i@2.0+x+ffr", pin_xy=desc)
    assert "(N face strip " in out


def test_x_row_inside_the_band_span_keeps_the_old_column_fill():
    mid = {b: (2500 + 1250 * b, 2700) for b in range(BITS)}    # pins level with the band, not beyond an edge
    old, _ = run(None, tag="ring:i@2.0+x+ff", pin_xy=mid)
    new, out = run("1", tag="ring:i@2.0+x+ff", pin_xy=mid)
    assert new == old and "pins not beyond the band's N/S edge: old column fill" in out


def test_gen_phys_exports_only_for_named_types():
    b = dict(cland_pinslot_types=["hd_turn_a", "slice_station"])
    assert gen_phys._cland_pinslot(b, "hd_turn_a") and gen_phys._cland_pinslot(b, "slice_station__t3")
    assert not gen_phys._cland_pinslot(b, "hd_turn_b") and not gen_phys._cland_pinslot({}, "hd_turn_a")


def test_gen_phys_pinslot_extra_from_gen_option():
    # AUTOBUILD-PIPE-1 (COORD 10-30 23:1x): gen phys --cland-pinslot all|TYPES adds to the plan list
    assert gen_phys._cland_pinslot({}, "slice_station__t23", ("all",))
    assert gen_phys._cland_pinslot({}, "slice_station__t23", ("slice_station",))
    assert not gen_phys._cland_pinslot({}, "hd_turn_b", ("slice_station",))
    assert not gen_phys._cland_pinslot({}, "hd_turn_b", ())


def test_export_only_type_gets_an_empty_land_slots():
    # AUTOBUILD-PIPE-1 (GEOM-84 t23): a declared clock export without a ring -> land_slots.json with no buses
    from clock_landings import LAND_SLOTS_SCHEMA
    t = {"clock": {"landing_contract": {"pins": [
        {"name": "arst_n", "dir": "in", "kind": "reset"},
        {"name": "fclk_out_cland_up", "dir": "out", "kind": "clock", "source_clock_port": "clk_t21"}]}}}
    assert gen_phys.export_land_slots(t, None) == {"schema": LAND_SLOTS_SCHEMA, "buses": {}}
    ring = {"schema": LAND_SLOTS_SCHEMA, "buses": {"ft0_i": {"D": 4, "form": "hold_mux"}}}
    assert gen_phys.export_land_slots(t, ring) is ring                      # a ring declaration is kept as is
    assert gen_phys.export_land_slots({"clock": {"landing_contract": {"pins": [
        {"name": "arst_n", "dir": "in", "kind": "reset"}]}}}, None) is None  # no export: unchanged (no file)
    assert gen_phys.export_land_slots({}, None) is None
    assert gen_phys.export_land_slots({"clock": None}, None) is None


def test_x_row_columns_stack_from_the_face_edge_and_skip_a_taken_slot():
    # 4 columns of 270 dbu (family width) over a 1.2-um band, 16 flops -> 4 per column at a 2-row pitch from the top
    rect, tag = "2 0 3.2 5.4", "ring:i@2.0+x+ff"
    new, out = run("1", tag=tag, pin_xy=NPIN, rect=rect)
    assert "(N face strip " in out and "4 columns" in out and "0 by the whole band" in out
    cols = {}
    for n, (x, y) in new.items():
        cols.setdefault(x, []).append(y)
    assert sorted(cols) == [2052, 2322, 2592, 2862]
    assert all(sorted(v) == [3240, 3780, 4320, 4860] for v in cols.values()), cols
    # a tapcell on the face row of the first column: that column starts one pitch down, nothing leaves the strip
    new, out = run("1", tag=tag, pin_xy=NPIN, rect=rect, occ="dict set cland_occ 18 {{2000 2100}}\n")
    assert "0 by the whole band" in out and all(y >= 2700 for x, y in new.values())
    assert all(not (x < 2100 and y <= 4860 < y + 540) for x, y in new.values())


def test_x_row_overflow_takes_the_nearest_column_to_its_left():
    # the last column is blocked over the whole strip: its flops fill the free strip slots of the nearest columns to its
    # left (column 2 has 2 free of 6, then column 1), never the strip's left end column 0
    rect, tag = "2 0 3.2 5.4", "ring:i@2.0+x+ff"
    occ = "".join(f"dict set cland_occ {r} {{{{2862 3200}}}}\n" for r in range(20))
    new, out = run("1", tag=tag, pin_xy=NPIN, rect=rect, occ=occ)
    assert "0 by the whole band" in out
    for n, (x, y) in new.items():
        bit = int(re.search(r"\]\[(\d+)\]$", n).group(1))
        assert x < 2862 and (bit < 6 or x in (2322, 2592)), (n, x, y)


@pytest.mark.parametrize("pins,face", [(NPIN, "N"), (SPIN, "S")])
def test_plain_ff_band_with_x_row_pins_takes_the_face_strip(pins, face):
    """AUTOBUILD-PIPE-2 10-31 (S81 stations: N-face buses on +ff bands, pinslot 'pins not a y column: old fill',
    GEOM-85 pin_reg_p90 45..94): a +ff band whose pins run along x beyond its N/S edge in key order is packed as the
    +x face strip; unset pinslot keeps the old fill"""
    old, _ = run(None, tag="ring:i+ff", pin_xy=pins)
    new, out = run("1", tag="ring:i+ff", pin_xy=pins)
    assert f"({face} face strip " in out and "+ff band as +x" in out, out
    assert len(new) == BITS * SLOTS
    _no_overlap(new)
    assert max(farthest_xy(new, pins).values()) < max(farthest_xy(old, pins).values())


def test_plain_ff_band_with_y_column_pins_is_unchanged():
    base, _ = run("1", tag="ring:i+ff")                    # W-face pins: the y-column stretch, as before
    _, out = run("1", tag="ring:i+ff")
    assert "stretched over pin y" in out and "+ff band as +x" not in out
    assert len(base) == BITS * SLOTS


def test_plain_ff_band_as_x_uses_every_row_of_the_strip():
    """AUTOBUILD-PIPE-2 10-31 (S81 t7__cl503f4913 p90 30.25 -> 23.97): the +ff-band-as-+x strip packs every row (100 %
    column density), half the depth of the +x tag form (2-row pitch), so each column's flops sit one row apart"""
    rect = "2 0 3.2 5.4"
    ff, out = run("1", tag="ring:i+ff", pin_xy=NPIN, rect=rect)
    x2, _ = run("1", tag="ring:i@2.0+x+ff", pin_xy=NPIN, rect=rect)
    assert "+ff band as +x" in out and "0 by the whole band" in out
    _no_overlap(ff)
    cols = {}
    for x, y in ff.values():
        cols.setdefault(x, []).append(y)
    assert all(sorted(v) == [4320, 4590, 4860, 5130] for v in cols.values()), cols
    assert min(y for x, y in ff.values()) > min(y for x, y in x2.values())


def test_e_face_pins_fill_from_the_band_e_edge():
    """AUTOBUILD-PIPE-4 10-31 (GEOM-87, HEAD hd_st_m E-face rx_i ring 108-128 um from its pins): pins beyond the band's
    E edge -> each row fills from the band's E (pin-side) edge; W-face bands keep the low-x fill (pin side)."""
    e_xy = {b: (13000, PIN_Y[b]) for b in range(BITS)}      # E-face pins i[b] at x 13 um, band x 2..12
    east, out = run("1", pin_xy=e_xy)
    west, _ = run("1")
    assert len(east) == len(west) == BITS * SLOTS and "E face, from the band E edge" in out
    # every flop sits within ~2 um of the band's E edge; the W-face run sits at its W edge
    assert min(x for x, _ in east.values()) >= 12000 - 2000 - 81
    assert max(x for x, _ in west.values()) <= 2000 + 2000
    # mirror of the W fill: same rows, same number of flops per row, no body overlap
    assert sorted(y for _, y in east.values()) == sorted(y for _, y in west.values())
    rows = {}
    for x, y in east.values():
        rows.setdefault(y, []).append(x)
    for xs in rows.values():
        xs.sort()
        assert all(b - a >= 81 for a, b in zip(xs, xs[1:]))
    # distance to the E pin: farthest slot of each bit is a few um, not the band width
    far = {b: max(13000 - x + abs(y + 135 - PIN_Y[b]) for n, (x, y) in east.items() if n.endswith(f"[{b}]"))
           for b in range(BITS)}
    assert max(far.values()) < 4000
