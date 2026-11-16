"""ft_throat_fix (S81-LEAF-PLAN 11-15, COORD r57 lever 2): a station band is rebuilt across the bundle to the track
use target, the free interval across the bundle at a station is read between the bounding macros, and a core push
moves the crowded macro group rigidly with the ft stations it would cover."""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import schema as S  # noqa: E402
import ft_nudge  # noqa: E402
import ft_seam_fix as SF  # noqa: E402
import ft_spread as FS  # noqa: E402
import ft_throat_fix as T  # noqa: E402
from tools.die_trial.legal_sites import RowAllocator  # noqa: E402


def macro(inst, x, y, w, h):
    return dict(inst=inst, lef="x.lef", origin_um=[x, y], outline_um=[w, h], orient="R0")


def ttype(contents, slots):
    return dict(outline_um=[600.0, 600.0], contents=contents, ft_slots=slots)


def alloc(t, skip_slot=None, skip_stage=None):
    boxes = [(a - 2, b - 2, c + 2, d + 2) for a, b, c, d in S.placed_macro_boxes(t).values()]
    al = RowAllocator((4.32, 4.32, 595.68, 595.68), blocked=boxes, cell_size=FS.CELL, column_pitch=2.16, row_pitch=.27,
                      origin=(4.32, 4.32))
    for x in t["ft_slots"]:
        for j, st in enumerate(x.get("bit_sites_um") or []):
            if x["name"] == skip_slot and j == skip_stage:
                continue
            for bx, by in st:
                al.reserve_rectangle((bx, by, bx + FS.CELL[0], by + FS.CELL[1]))
    return al


def test_band_meets_target_and_keeps_bit_order():
    W = 600
    s = dict(name="ft0", width=W, in_face="W", out_face="E", layers=["M4", "M6"], stations=2)
    narrow = [[300.0 + 2.16 * (i % 40), 300.0 + .27 * (i // 40)] for i in range(W + 1)]    # 40 columns, 4 um high
    s["bit_sites_um"] = [narrow]
    assert T.u_stations(s)[0] > 1.0
    t = ttype([], [s])
    tpu = FS._tracks(s, True)
    ext = W / (T.TARGET * tpu) / 0.95 + FS.CELL[1]
    order = T.ranks(narrow, True)
    g = T.band(alloc(t, "ft0", 0), (300.0, 300.0), order, W + 1, ext, True, FS.CELL)
    s["bit_sites_um"] = [g]
    assert T.u_stations(s)[0] <= T.TARGET
    ys = [g[i][1] for i in sorted(range(W + 1), key=lambda i: order[i])]
    assert ys == sorted(ys)                          # bits keep their order across the bundle


def test_throat_reads_the_gap_between_bounding_macros():
    t = ttype([macro("lo", 100, 100, 200, 100), macro("hi", 100, 220, 200, 100)], [])
    lo, hi, mlo, mhi = T.throat(t, (200.0, 210.0), 40.0, 10.0, True)
    assert (mlo, mhi) == ("lo", "hi") and abs(lo - 202.0) < 1e-9 and abs(hi - 218.0) < 1e-9
    assert T.throat(t, (200.0, 150.0), 40.0, 10.0, True) is None          # centre inside a macro: no throat read


def test_push_moves_crowded_group_and_its_stations(monkeypatch):
    monkeypatch.setattr(ft_nudge, "clock_points", lambda t: [])
    monkeypatch.setattr(SF, "allocator", alloc)
    s = dict(name="ft1", width=3, in_face="S", out_face="N", stations=2, regs_um=[[350.0, 0.0], [349.0, 330.0]],
             bit_site_cell_um=list(FS.CELL), bit_sites_um=[[[345.0, 330.0], [347.16, 330.0], [349.32, 330.0], [351.48, 330.0]]])
    t = ttype([macro("hi", 100, 220, 200, 100), macro("hi2", 100, 323, 200, 50)], [s])
    o = T.push_ok(t, "hi", 30.0, 1)
    assert o and sorted(o["group"]) == ["hi", "hi2"] and abs(o["um"] - 30.24) < 1e-9
    assert t["contents"][0]["origin_um"][1] == 250.24 and t["contents"][1]["origin_um"][1] == 353.24
    assert o["slots"] == []                         # station at x 345..353 is clear of the boxes (x 100..300)
    T.undo(o)
    assert t["contents"][0]["origin_um"] == [100, 220]
    assert T.push_ok(t, "hi", 300.0, 1) is None     # pushed past the outline


def test_push_station_follows_core():
    t = ttype([macro("m", 100, 100, 100, 100)], [])
    s = dict(name="ft0", width=1, in_face="W", out_face="E", stations=2, regs_um=[[0.0, 230.0], [150.0, 205.0]],
             bit_site_cell_um=list(FS.CELL), bit_sites_um=[[[150.0, 205.0], [152.16, 205.0]]])
    t["ft_slots"] = [s]
    import pytest
    mp = pytest.MonkeyPatch()
    mp.setattr(ft_nudge, "clock_points", lambda t: [])
    mp.setattr(SF, "allocator", alloc)
    try:
        o = T.push_ok(t, "m", 10.8, 1)              # box top 200 -> 210.8 covers the station at y 205
        assert o and o["slots"] == ["ft0"]
        ys = [p[1] for p in s["bit_sites_um"][0]]
        assert min(ys) >= 210.8 + 2.0 - 1e-6        # moved with the core, off its keep-off
        T.undo(o)
        assert s["bit_sites_um"][0][0] == [150.0, 205.0]
    finally:
        mp.undo()
