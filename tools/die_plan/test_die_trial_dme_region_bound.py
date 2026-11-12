"""HEAD-LEP0N-BAL: --region-dme-actual-max-region (per-region physical stage bound; other regions byte-identical)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_trial as D


class Site:
    """a 600 um core column at x 100..700 with no legal site; its nearest() snaps onto the column's E edge"""
    W, H = 1200., 1200.

    def legal(self, q):
        return 0 <= q[0] <= self.W and 0 <= q[1] <= self.H and not (100 < q[0] < 700 and 201 < q[1] < 899)

    def nearest(self, q, axis=None):
        return q if self.legal(q) else (700.6, q[1])


@pytest.fixture(autouse=True)
def mode(monkeypatch):
    monkeypatch.setattr(D, "DME_ACTUAL_MAX_UM", 405.)
    monkeypatch.setattr(D, "EVEN_LEGS", False)
    monkeypatch.setattr(D, "DME_ACTUAL_MAX_REGION", {"lep0N": 160.})


def _span(pl):
    return max(D._man(x, y) for x, y in zip(pl["chain"], pl["chain"][1:]))


def test_parse():
    assert D.parse_region_um("lep0N:160,mesh0S:200.5") == {"lep0N": 160., "mesh0S": 200.5}
    assert D.parse_region_um("") == {}
    for bad in ("lep0N", "lep0N:0", "lep0N:-3", "lep0N:inf"):
        with pytest.raises(ValueError):
            D.parse_region_um(bad)


def test_listed_region_takes_its_bound_and_others_do_not():
    a, b = (400., 900.), (400., 200.)
    base = D.physical_leg(Site(), a, b, 150.)
    with D.region_bound("sp3"):             # not listed: the die-wide bound, the same (cached) leg
        assert D.physical_leg(Site(), a, b, 150.) == base
    with D.region_bound("lep0N"):
        tight = D.physical_leg(Site(), a, b, 150.)
    assert _span(base) > 160. and _span(tight) <= 160. + 1e-6
    assert all(Site().legal(q) for q in tight["chain"])
    assert tight["delay_ps"] == pytest.approx(D.chain_ps(tight["chain"]))
    assert D._REGION_BOUND is None          # restored on exit
    assert D.physical_leg(Site(), a, b, 150.) == base


def test_region_tree_default_unchanged(monkeypatch):
    taps = [("p", "t0", 400., 950.), ("p", "t1", 400., 150.), ("p", "t2", 1000., 500.)]
    kw = dict(delay_rep_um=150.)
    a = D._dme_timed(Site(), taps, kw, "sp3")
    monkeypatch.setattr(D, "DME_ACTUAL_MAX_REGION", None)
    b = D._dme_timed(Site(), taps, kw, "sp3")
    assert a == b
