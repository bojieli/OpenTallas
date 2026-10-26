"""die_ft_bands GRT capacity model (die_trial.band_region_adjust / band_share_obs).

Strips: one owner per gcell, one gcell thick across the layer direction, none on the zero-capacity last edge line.
Transition layers (DIE-FT 2026-10-25): OpenROAD adjustTransitionLayers halves M5/M6 above a macro OBS on the layer
below, from the capacity before obstructions, so an uncompensated 75 % strip there kept 0 tracks (HBM edge+band root
interior, 8,806 zero-capacity gcells).  Over those gcells the strip obstructs (1 - 0.5) * (1 - a) so the kept capacity
equals the layer-adjustment model (0.5 * a)."""
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_trial as T  # noqa: E402

G = 10800   # gcell in DBU (1000/um)
g = T.GCELL_UM


def _tiles(r):
    x0, y0, x1, y1 = (round(v * 1000) for v in r[:4])
    return [(i, j) for i in range(x0 // G, x1 // G + 1) for j in range(y0 // G, y1 // G + 1)]


def _check(regs, vertical, W, H):
    own = Counter(t for r in regs for t in _tiles(r))
    assert own and max(own.values()) == 1
    nx, ny = T._ngrid(W), T._ngrid(H)
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
        _check(T._gstrips(T._uncovered(W, H, holes), vertical, W, H), vertical, W, H)


def test_strips_keep_extra_fields_and_drop_empty():
    out = T._gstrips([(0, 0, 3.0, 50.0, 0.5), (0, 0, 30.0, 32.4, 0.25)], False, 100.0, 100.0)
    assert len(out) == 3 and all(r[4] == 0.25 for r in out) and abs(out[0][2] - 32.39) < 1e-6


class _P:
    """216 x 216 um die (20 x 20 gcells); one part 'u' at (54, 54) whose type has one hard core (10, 10)-(98, 98)
    without a LEF (core_obs top M5 -> abstract OBS M4-M5), and an EW band over M6/M7 in its top 10.8 um."""
    W = H = 216.0
    layers = {"M4": {"dir": "H"}, "M5": {"dir": "V"}, "M6": {"dir": "H"}, "M7": {"dir": "V"}}
    layer_budget = {"partition_signal_max": "M7"}
    types = {"t": {"outline_um": [108.0, 108.0],
                   "hard_cores": [{"origin_um": [10.0, 10.0], "outline_um": [88.0, 88.0], "module": "c"}],
                   "die_ft_bands": [{"dir": "EW", "span_um": [97.2, 108.0], "layers": ["M6", "M7"]}]}}
    parts = {"u": {"type": "t", "origin_um": [54.0, 54.0]}}


class _Pempty(_P):
    types = {"t": {"outline_um": [108.0, 108.0], "hard_cores": []}}


def test_band_share_obs_blocks_the_unkept_part_of_each_gcell():
    regs = [("M6", 0.0, 10.8, 43.19, 21.59, 0.25), ("M7", 21.6, 0.0, 32.39, 43.19, 0.25), ("M6", 0, 0, 10.79, 10.79, 1.0)]
    out = T.band_share_obs(_Pempty, regs)
    assert len(out) == 2
    L, x0, y0, x1, y1 = out[0]
    assert L == "M6" and (x0, x1) == (0.0, 43.2) and abs(y0 - 13.5) < 1e-9 and abs(y1 - 21.6) < 1e-9
    L, x0, y0, x1, y1 = out[1]
    assert L == "M7" and abs(x0 - 24.3) < 1e-9 and abs(x1 - 32.4) < 1e-9 and (y0, y1) == (0.0, 43.2)


def test_transition_intervals_follow_openroad_tile_loop():
    # core die rect (64, 64)-(152, 152); M6 halving uses the M5 (V) OBS extended in x by 0.072:
    # first tile (5, 5), last tile (14, 14) -> rows 5..13, columns [5, 14) (last tile excluded)
    tr = T.transition_intervals(_P, "M6")
    assert sorted(tr) == list(range(5, 14)) and all(v == [(5, 14)] for v in tr.values())
    assert T.transition_intervals(_P, "M7") == {}          # M7 is not a transition layer
    assert set(T.transition_intervals(_P, "M5")) == set(range(5, 14))   # M5 over the M4 OBS (columns)


def test_strip_over_core_is_compensated_for_the_transition_halving():
    regs = [("M6", 0.0, 8 * g, round(19 * g - 0.01, 3), round(9 * g - 0.01, 3), 0.25)]
    out = T.band_share_obs(_P, regs)
    assert [(round(x0 / g), round(x1 / g)) for _, x0, _, x1, _ in out] == [(0, 5), (5, 14), (14, 19)]
    keep = [round(((y1 - y0) / g), 6) for _, _, y0, _, y1 in out]
    # obstructed fraction: 0.75 off the core, 0.5 * 0.75 = 0.375 over it (OpenROAD then halves -> kept 0.125)
    assert keep == [0.75, 0.375, 0.75]
    assert all(abs(y1 - 9 * g) < 1e-9 for _, _, _, _, y1 in out)      # obstruct the top of the row


def test_strips_cover_cores_no_halo_and_band_keeps_all():
    bl, regs = T.band_region_adjust(_P, 0.75)
    assert bl == ["M6", "M7"]
    m6 = [r for r in regs if r[0] == "M6"]
    rows = Counter(round(r[2] / g) for r in m6)
    # band: the type's top 10.8 um = die (54, 151.2)-(162, 162) -> row 14 keeps share strips only left and right of it
    assert rows[14] == 2 and all(rows[j] == 1 for j in range(0, 14)) and all(rows[j] == 1 for j in range(15, 20))
    r14 = sorted((r[1], r[3]) for r in m6 if round(r[2] / g) == 14)
    assert r14[0][1] < 54.0 and r14[1][0] >= 162.0 - 1e-6
    # rows over the core (5..13) are full-width strips: the core is no longer cut out with a 12 um halo
    assert all(r[1] == 0.0 and abs(r[3] - (19 * g - 0.01)) < 1e-6 for r in m6 if 5 <= round(r[2] / g) <= 13)
    assert all(r[5] == 0.25 for r in regs)


def test_grid_count_is_integer_dbu():
    assert T._ngrid(216.0) == 20 and T._ngrid(215.99) == 19 and T._ngrid(28399.68) == 2629
