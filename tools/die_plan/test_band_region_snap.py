"""die_ft_bands GRT region strips (DIE-FT-HBM 2026-10-25): one owner per gcell, one gcell thick across the layer
direction (OpenROAD border-tile formula, see die_trial._gstrips), no strip on the zero-capacity last edge line."""
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_trial as T  # noqa: E402

G = 10800   # gcell in DBU (1000/um)


def _tiles(r):
    x0, y0, x1, y1 = (round(v * 1000) for v in r[:4])
    return [(i, j) for i in range(x0 // G, x1 // G + 1) for j in range(y0 // G, y1 // G + 1)]


def _check(regs, vertical, W, H):
    own = Counter(t for r in regs for t in _tiles(r))
    assert own and max(own.values()) == 1
    nx, ny = int(W // 10.8), int(H // 10.8)
    for r in regs:
        ts = _tiles(r)
        if vertical:
            assert len({i for i, _ in ts}) == 1 and max(j for _, j in ts) <= ny - 2
        else:
            assert len({j for _, j in ts}) == 1 and max(i for i, _ in ts) <= nx - 2


def test_strips_disjoint_one_thick_and_off_last_edge():
    W, H = 1000.32, 700.0
    holes = [(103.3, 55.1, 260.9, 333.7), (400.05, 420.2, 777.7, 600.6), (0, 200.13, W, 213.4)]
    for vertical in (False, True):
        regs = T._gstrips(T._uncovered(W, H, holes), vertical, W, H)
        _check(regs, vertical, W, H)


def test_strips_keep_extra_fields_and_drop_empty():
    out = T._gstrips([(0, 0, 3.0, 50.0, 0.5), (0, 0, 30.0, 32.4, 0.25)], False, 100.0, 100.0)
    assert len(out) == 3 and all(r[4] == 0.25 for r in out) and abs(out[0][2] - 32.39) < 1e-6


class _P:
    layers = {"M6": {"dir": "H"}, "M7": {"dir": "V"}}


def test_band_share_obs_blocks_the_unkept_part_of_each_gcell():
    regs = [("M6", 0.0, 10.8, 43.19, 21.59, 0.25), ("M7", 21.6, 0.0, 32.39, 43.19, 0.25), ("M6", 0, 0, 10.79, 10.79, 1.0)]
    out = T.band_share_obs(_P, regs)
    assert len(out) == 2
    L, x0, y0, x1, y1 = out[0]
    assert L == "M6" and (x0, x1) == (0.0, 43.2) and abs(y0 - 13.5) < 1e-9 and abs(y1 - 21.6) < 1e-9
    L, x0, y0, x1, y1 = out[1]
    assert L == "M7" and abs(x0 - 24.3) < 1e-9 and abs(x1 - 32.4) < 1e-9 and (y0, y1) == (0.0, 43.2)
