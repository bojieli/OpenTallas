import importlib.util
import re
from pathlib import Path

spec = importlib.util.spec_from_file_location("pts", Path(__file__).with_name("pin_track_snap.py"))
pts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pts)

RX = re.compile(r"^clk_")
PIN = dict(bus="clk_t19", bit=None, layer="M7", x=23.328, y=338.592, native_rects=[["M7", 23.312, 338.208, 23.344, 338.976]])
IO = ('set ot_mp_bt [[ord::get_db_block] findBTerm {clk_t19}]\n'
      'odb::dbBox_create $ot_mp_bp [[ord::get_db_tech] findLayer M7] [expr {int(round(23.312000*$ot_mp_u))}] '
      '[expr {int(round(338.208000*$ot_mp_u))}] [expr {int(round(23.344000*$ot_mp_u))}] [expr {int(round(338.976000*$ot_mp_u))}]\n')


def test_derive_t51_native_e_r0_plus4():
    s, res = pts.derive_shift([PIN], "M7", RX, [639.36, 8.64], [0.108, 0.012], [794.88, 1209.6])
    assert s == 4 and res == {60: 1}


def test_mirror_flips_sign():
    # same absolute residue in a MY core: the own-frame shift is the opposite sign
    s, _ = pts.derive_shift([PIN], "M7", RX, [639.36, 8.64], [0.108, 0.012], [794.88, 1209.6], "MY")
    assert s != 4


def test_snap_pins_and_io_land_on_track():
    pins = [dict(PIN, native_rects=[list(b) for b in PIN["native_rects"]])]
    s, _ = pts.derive_shift(pins, "M7", RX, [639.36, 8.64], [0.108, 0.012], [794.88, 1209.6])
    assert pts.shift_pin_rows(pins, "M7", RX, s) == 1
    assert pins[0]["x"] == 23.332 and pins[0]["native_rects"][0][1:4:2] == [23.316, 23.348]
    t, n = pts.shift_io_tcl(IO, "M7", RX, s)
    assert n == 1 and "23.316000" in t and "23.348000" in t and "338.208000" in t
    s2, res = pts.derive_shift(pins, "M7", RX, [639.36, 8.64], [0.108, 0.012], [794.88, 1209.6])
    assert s2 == 0 and res == {0: 1}


def test_mixed_residues_refused():
    import pytest
    pins = [PIN, dict(PIN, bus="clk_t2", x=23.34)]
    with pytest.raises(SystemExit):
        pts.derive_shift(pins, "M7", RX, [639.36, 8.64], [0.108, 0.012], [794.88, 1209.6])


def test_clock_roots_entries_shift():
    d = {"entries": [dict(pin="clk_t19", plan_xy_um=[23.328, 338.592, "M7"]), dict(pin="clk_x", plan_xy_um=[1.0, 2.0, "M5"])]}
    assert pts.shift_clock_roots(d, "M7", RX, 4) == 1
    assert d["entries"][0]["plan_xy_um"][0] == 23.332 and d["entries"][1]["plan_xy_um"][0] == 1.0
