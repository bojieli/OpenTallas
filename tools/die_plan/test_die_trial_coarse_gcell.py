"""DIE-PROTO-1 coarse-gcell form (COORD 11-12): die_trial GCELL_UM follows --coarse-um (gcell = 15 x coarse), so the
band_share strips / transition intervals / tile counts are snapped to the GRT tile that OpenROAD actually uses.
Check: a die scaled by k with coarse k x 0.72 gives the default (10.8 um) result scaled by k."""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_trial as T  # noqa: E402
import test_band_capmodel as C  # noqa: E402


@pytest.fixture(autouse=True)
def _restore():
    g0 = T.GCELL_UM
    yield
    T.GCELL_UM = g0


def _scaled(Pc, k):
    class Q(Pc):
        W = H = Pc.W * k
        types = {tn: dict(t, outline_um=[v * k for v in t["outline_um"]],
                          hard_cores=[dict(h, origin_um=[v * k for v in h["origin_um"]],
                                           outline_um=[v * k for v in h["outline_um"]]) for h in t.get("hard_cores", [])],
                          **({"die_ft_bands": [dict(b, span_um=[v * k for v in b["span_um"]]) for b in t["die_ft_bands"]]}
                             if "die_ft_bands" in t else {}))
                 for tn, t in Pc.types.items()}
        parts = {pn: dict(p, origin_um=[v * k for v in p["origin_um"]]) for pn, p in Pc.parts.items()}
    return Q


def _norm(rs, g):
    """layer, gcell coords (x0, y0) in gcell units, then the kept fraction unchanged"""
    return sorted((r[0], round(r[1] / g, 4), round(r[2] / g, 4)) + tuple(r[3:]) for r in rs)


def test_setter_and_default():
    assert T.GCELL_UM == 10.8 and T.GCELL_PITCHES == 15
    assert T.set_gcell_from_coarse(2.16) == 32.4 and T.GCELL_UM == 32.4
    assert T._ngrid(28399.68) == 876                   # HBM d55a at 32.4 um (OpenROAD: 877 tiles incl. partial)
    with pytest.raises(ValueError):
        T.set_gcell_from_coarse(0)
    with pytest.raises(ValueError):
        T.set_gcell_from_coarse(math.nan)


@pytest.mark.parametrize("k", [2, 3])
def test_transition_intervals_scale(k):
    base = {L: T.transition_intervals(C._P, L) for L in ("M5", "M6", "M7")}
    T.set_gcell_from_coarse(0.72 * k)
    Q = _scaled(C._P, k)
    assert {L: T.transition_intervals(Q, L) for L in ("M5", "M6", "M7")} == base


@pytest.mark.parametrize("k", [2, 3])
def test_band_region_and_share_obs_scale(k):
    g0 = T.GCELL_UM
    bl0, regs0 = T.band_region_adjust(C._P, 0.75, core_zero=False)
    obs0 = T.band_share_obs(C._P, regs0)
    T.set_gcell_from_coarse(0.72 * k)
    Q = _scaled(C._P, k)
    bl1, regs1 = T.band_region_adjust(Q, 0.75, core_zero=False)
    obs1 = T.band_share_obs(Q, regs1)
    assert bl1 == bl0
    assert len(regs1) == len(regs0) and len(obs1) == len(obs0)
    # same gcell rows/columns and same kept fractions in gcell units (eps pull-ins are absolute 0.01 um)
    assert _norm([r[:1] + tuple(r[1:3]) + r[5:] for r in regs1], T.GCELL_UM) == \
        _norm([r[:1] + tuple(r[1:3]) + r[5:] for r in regs0], g0)
    assert [(L, round(x0 / T.GCELL_UM, 3), round(y0 / T.GCELL_UM, 3), round(x1 / T.GCELL_UM, 2), round(y1 / T.GCELL_UM, 2))
            for L, x0, y0, x1, y1 in sorted(obs1)] == \
        [(L, round(x0 / g0, 3), round(y0 / g0, 3), round(x1 / g0, 2), round(y1 / g0, 2)) for L, x0, y0, x1, y1 in sorted(obs0)]


def test_explicit_g_still_wins():
    T.set_gcell_from_coarse(2.16)
    assert T._ngrid(216.0, 10.8) == 20 and T._ngrid(216.0) == 6
