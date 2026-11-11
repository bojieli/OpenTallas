"""FTRES-FIX 11-10 (owner-approved, COORD ftres-why-hbm-only): die FT ownership over hard cores.

(1) outside a band the die keeps 0 over a planned hard-core footprint (12.10c), so the partition reserves nothing there;
(2) over a halved transition gcell (M6 over an M5-OBS core) the partition reserves the die's real capacity 0.5 a, not
    the complement 1 - fh = 0.5 + 0.5 a of the GRT stripes;
(3) a band's core_share (the type's own measured need) sets the die share over cores inside that band.
The die GRT capacity model (band_share_obs owner=False) keeps its transition compensation; the ownership map is a subset
of its free part, so the partition reservation never double-owns a die GRT track."""
import copy
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_trial as T  # noqa: E402
from tools.die_plan import schema, partition_ft_reserve as F  # noqa: E402

g = T.GCELL_UM


class _P:
    """216 x 216 die, part u at (54, 54), type 108 x 108 with one M5 core (10,10)-(98,98) -> die (64,64)-(152,152);
    EW band over M6/M7 in the type's top 10.8 um (die rows 14)."""
    W = H = 216.0
    layers = {"M4": {"dir": "H"}, "M5": {"dir": "V"}, "M6": {"dir": "H"}, "M7": {"dir": "V"}}
    layer_budget = {"partition_signal_max": "M7"}
    types = {"t": {"outline_um": [108.0, 108.0],
                   "hard_cores": [{"origin_um": [10.0, 10.0], "outline_um": [88.0, 88.0], "module": "c"}],
                   "die_ft_bands": [{"dir": "EW", "span_um": [97.2, 108.0], "layers": ["M6", "M7"]}]}}
    parts = {"u": {"type": "t", "origin_um": [54.0, 54.0]}}


def _tiles(r):
    G = 10800
    x0, y0, x1, y1 = (round(v * 1000) for v in r[:4])
    return [(i, j) for i in range(x0 // G, x1 // G + 1) for j in range(y0 // G, y1 // G + 1)]


def test_core_zero_one_owner_per_gcell_and_zero_over_core():
    bl, regs = T.band_region_adjust(_P, 0.75, core_zero=True)
    assert bl == ["M6", "M7"]
    for L in bl:
        rs = [r for r in regs if r[0] == L]
        own = Counter(t for r in rs for t in _tiles(r[1:]))
        assert max(own.values()) == 1
        share = {t: r[5] for r in rs for t in _tiles(r[1:])}
        # core gcells 6..13 x 6..13 keep 0, a gcell well outside keeps the default 0.25
        assert all(share[(i, j)] == 0.0 for i in range(6, 13) for j in range(6, 13))
        assert share[(1, 1)] == 0.25 and share[(17, 3)] == 0.25


def test_core_zero_off_is_the_old_model():
    _, a = T.band_region_adjust(_P, 0.75, core_zero=False)
    assert all(r[5] == 0.25 for r in a)


def test_band_core_share_sets_share_over_cores_inside_the_band():
    class _Q(_P):
        types = copy.deepcopy(_P.types)
    _Q.types["t"]["die_ft_bands"] = [{"dir": "EW", "span_um": [40.0, 61.6], "layers": ["M7"], "die_share": 1.0,
                                     "core_share": 0.1}]
    _, regs = T.band_region_adjust(_Q, 0.75, core_zero=True)
    share = {t: r[5] for r in regs for t in _tiles(r[1:])}
    # band die rows y 94..115.6 -> gcell rows 9..10; over the core (cols 6..13) 0.1, outside the core die_share 1
    assert share[(8, 9)] == 0.1 and share[(8, 10)] == 0.1
    assert (5, 9) not in share and (14, 9) not in share        # in the band off the core: die_share 1.0, no strip
    assert share[(2, 9)] == 0.25                                # outside the partition: default
    assert share[(8, 7)] == 0.0                                 # core outside the band


def test_owner_map_reserves_real_capacity_over_halved_gcells():
    regs = [("M6", 0.0, 8 * g, round(19 * g - 0.01, 3), round(9 * g - 0.01, 3), 0.25)]
    grt = T.band_share_obs(_P, regs)
    own = T.band_share_obs(_P, regs, owner=True)
    obs = lambda out: [round((y1 - y0) / g, 6) for _, _, y0, _, y1 in out]
    assert obs(grt) == [0.75, 0.375, 0.75]       # GRT capacity model unchanged (OpenROAD halves -> 0.125 kept)
    assert obs(own) == [0.75, 0.875, 0.75]       # the die owns only 0.125 of the halved row
    # a = 1 band over a halved row: the die owns its real half, not the whole row
    full = [("M6", 0.0, 8 * g, round(19 * g - 0.01, 3), round(9 * g - 0.01, 3), 1.0)]
    assert T.band_share_obs(_P, full) == []
    o = T.band_share_obs(_P, full, owner=True)
    assert len(o) == 1 and [round((o[0][3] - o[0][1]) / g), round((o[0][4] - o[0][2]) / g, 6)] == [9, 0.5]
    # a = 0 over a core: the die owns nothing
    zero = [("M6", 0.0, 8 * g, round(19 * g - 0.01, 3), round(9 * g - 0.01, 3), 0.0)]
    assert obs(T.band_share_obs(_P, zero, owner=True)) == [1.0, 1.0, 1.0]


def test_owner_slice_is_inside_the_grt_free_slice():
    for a in (0.0, 0.25, 0.5, 1.0):
        regs = [("M6", 0.0, 8 * g, round(19 * g - 0.01, 3), round(9 * g - 0.01, 3), a)]
        grt = {round(r[1] / g): (r[2], r[4]) for r in T.band_share_obs(_P, regs)}
        for r in T.band_share_obs(_P, regs, owner=True):
            k = round(r[1] / g)
            if k in grt:      # both obstruct the top of the row; the owner obstruction is at least as long
                assert abs(r[4] - grt[k][1]) < 1e-9 and r[2] <= grt[k][0] + 1e-9


def _plan(core_share=None, band=True):
    raw = json.loads((Path(schema.__file__).parent / 'examples/tiny_plan.json').read_text())
    raw['ports'] = []; raw['lanes'] = []
    raw['partitions'] = raw['partitions'][:1]
    typ = raw['partitions'][0]['type']; t = raw['partition_types'][typ]
    t['hard'] = False
    # one M5 core at (216, 216)-(648, 648) of the 864 x 864 type
    t['hard_cores'] = [dict(inst='u_c', module='c', origin_um=[216.0, 216.0], outline_um=[432.0, 432.0],
                            obs_max='M5')]
    b = dict(dir='NS', span_um=[324.0, 432.0], layers=['M7'], die_share=1.0)
    if core_share is not None:
        b['core_share'] = core_share
    t['die_ft_bands'] = [b, dict(dir='EW', span_um=[0.0, 864.0], layers=['M6'], die_share=0.25)] if band else []
    return schema.Plan(raw), typ


def _inside(rows, L, x, y):
    return any(r['layer'] == L and r['rect'][0] < x < r['rect'][2] and r['rect'][1] < y < r['rect'][3] for r in rows)


def _share(rows, L, x0, y0, x1, y1):
    """reserved area fraction of the box on layer L (rows are disjoint per layer)"""
    a = 0.0
    for r in rows:
        if r['layer'] != L:
            continue
        q = T._rect_and(r['rect'], (x0, y0, x1, y1))
        if q:
            a += (q[2] - q[0]) * (q[3] - q[1])
    return a / ((x1 - x0) * (y1 - y0))


def test_reservation_zero_over_core_outside_bands_and_core_share_inside():
    P, typ = _plan(core_share=0.1)
    r = F.reservation(P, typ)['rectangles_um']
    # M7 over the core, outside the NS band: nothing reserved; outside the core it keeps the default quarter
    assert _share(r, 'M7', 237.6, 237.6, 313.2, 626.4) == pytest.approx(0.0)
    assert _share(r, 'M7', 10.8, 10.8, 194.4, 205.2) == pytest.approx(0.25, abs=0.01)
    # M7 in the band over the core: the measured need 0.1; in the band off the core: die_share 1
    assert _share(r, 'M7', 334.8, 237.6, 421.2, 626.4) == pytest.approx(0.1, abs=0.01)
    assert _share(r, 'M7', 334.8, 10.8, 421.2, 194.4) == pytest.approx(1.0, abs=0.01)
    # M6 over the M5 core (halved transition rows) in a 0.25 band: the die's real 0.125, not 0.625
    assert _share(r, 'M6', 237.6, 248.4, 615.6, 615.6) == pytest.approx(0.125, abs=0.01)


def test_reservation_never_double_owns_die_tracks_with_cores():
    P, typ = _plan(core_share=0.1)
    _, regs = T.band_region_adjust(P, .75)
    grt = [dict(layer=L, rect=list(q)) for L, *q in T.band_share_obs(P, regs)]
    own_map = [dict(layer=L, rect=list(q)) for L, *q in T.band_share_obs(P, regs, owner=True)]
    res = F.reservation(P, typ)['rectangles_um']
    for L in ('M6', 'M7'):
        for x in (5.0, 100.0, 300.0, 350.0, 500.0, 700.0):
            for y in (2.0, 7.5, 260.0, 263.3, 300.1, 500.2, 800.4):
                if _inside(res, L, x, y):
                    # partition-reserved = die-owned: never under a die GRT obstruction, never under the owner map
                    assert not _inside(grt, L, x, y) and not _inside(own_map, L, x, y)
                elif not any(c[0] < x < c[2] and c[1] < y < c[3] for c in T.die_core_rects(P, L)):
                    assert _inside(own_map, L, x, y)


def test_no_band_type_unchanged():
    P, typ = _plan(band=False)
    assert F.reservation(P, typ) is None


def test_schema_accepts_core_share():
    P, typ = _plan(core_share=0.3)
    errs = list(schema.validate(P.raw)) if hasattr(schema, 'validate') else []
    assert not [e for e in errs if 'core_share' in str(e)]
