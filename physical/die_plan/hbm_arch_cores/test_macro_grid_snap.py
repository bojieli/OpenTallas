#!/usr/bin/env python3
"""HBM-CORES-REBAL-9 (FG2 (f) macro_pin_grid): gen_core_kit_hbm.snap_macro_placement puts every signal pin of a
static macro on the kit's preferred-direction track grid with the smallest origin move; on-grid tables are unchanged;
impossible / overlapping / out-of-outline results fail closed.
  python3 -m pytest physical/die_plan/hbm_arch_cores/test_macro_grid_snap.py"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_core_kit_hbm as GK  # noqa: E402

ROOT = HERE.parents[2]
SRAM = "ot_sram_1r1w_128x256_m1_r2c2"
LEF = ROOT / f"physical/asap7_memory_macros_v2/{SRAM}/{SRAM}.lef"
TRACKS = "make_tracks M4 -x_offset 0.024 -x_pitch 0.048 -y_offset 0.024 -y_pitch 0.048\n" + GK.M123_TRACKS
TOY = """MACRO toy
  SIZE 1.0 BY 0.5 ;
  PIN a
    USE SIGNAL ;
    PORT
      LAYER M4 ;
        RECT 0.0 0.100 0.2 0.124 ;
    END
  END a
  PIN b
    USE SIGNAL ;
    PORT
      LAYER M5 ;
        RECT 0.300 0.0 0.324 0.2 ;
    END
  END b
  PIN VDD
    USE POWER ;
    PORT
      LAYER M4 ;
        RECT 0.0 0.001 1.0 0.025 ;
    END
  END VDD
END toy
"""


def _snap(pl, lef=TOY, outline=(100.0, 100.0)):
    return GK.snap_macro_placement(pl, TRACKS, lambda m: lef, outline)


def _on_grid(p, lef=TOY):
    w, h, rects = GK.lef_signal_pins(lef, p["macro"])
    offs = GK.kit_track_offsets(TRACKS)
    x, y = (GK._nm(c) for c in p["xy_um"])
    for L, *r in rects:
        d, pitch, wd = GK.TECH_TRACK_LAYERS[L]
        X0, Y0, X1, Y1 = GK._oriented(r, p.get("orient", "R0"), w, h)
        lo, hi = (x + X0, x + X1) if d == "V" else (y + Y0, y + Y1)
        assert GK._on_track(lo, hi, wd, pitch, offs[L]), (p, L)


def test_offsets_from_kit_tracks():
    o = GK.kit_track_offsets(TRACKS)
    assert o["M4"] == [24] and o["M3"] == [9] and o["M2"] == [45, 81]   # M2 kit lines use pitch 0.27 -> platform
    assert o["M5"] == [12]                                                # layer not in the kit file -> platform


@pytest.mark.parametrize("orient", ["R0", "MX", "MY", "R180"])
def test_toy_snaps_both_axes_minimally(orient):
    p = dict(inst="u", macro="toy", xy_um=[10.0, 20.0], orient=orient)
    (q,), moves = _snap([p])
    _on_grid(q)
    assert len(moves) <= 1
    if moves:
        assert abs(moves[0]["dx_nm"]) <= 24 and abs(moves[0]["dy_nm"]) <= 24
    (r,), again = _snap([q])
    assert r == q and again == []                                   # idempotent: on-grid input unchanged


def test_on_grid_table_is_returned_unchanged():
    p = dict(inst="u", macro="toy", xy_um=[10.0, 20.0], orient="R0")
    (q,), _ = _snap([p])
    out, moves = _snap([dict(q)])
    assert out == [q] and moves == []


def test_fail_closed():
    with pytest.raises(SystemExit):                                  # off the outline after the move
        _snap([dict(inst="u", macro="toy", xy_um=[99.0, 99.6], orient="R0")])
    with pytest.raises(SystemExit):                                  # overlap
        _snap([dict(inst="u", macro="toy", xy_um=[10.0, 20.0]), dict(inst="v", macro="toy", xy_um=[10.5, 20.0])])
    bad = TOY.replace("RECT 0.0 0.100 0.2 0.124", "RECT 0.0 0.100 0.2 0.112")   # 12-nm pin: no track fits
    with pytest.raises(SystemExit):
        _snap([dict(inst="u", macro="toy", xy_um=[10.0, 20.0])], lef=bad)


@pytest.mark.skipif(not LEF.is_file(), reason="SRAM LEF not present")
@pytest.mark.parametrize("orient,y", [("R0", 476.55), ("MX", 99.36), ("MY", 576.18), ("R0", 558.9)])
def test_sram_lanes_canon_sites(orient, y):
    """the lanes__canon _c20ek2m SRAM sites the FG2 check flagged 6-24 nm off M4."""
    lef = LEF.read_text()
    p = dict(inst="u", macro=SRAM, xy_um=[34.722, y], orient=orient)
    (q,), moves = _snap([p], lef=lef, outline=(760.32, 725.76))
    _on_grid(q, lef)
    assert moves and moves[0]["dx_nm"] == 0 and abs(moves[0]["dy_nm"]) <= 24
