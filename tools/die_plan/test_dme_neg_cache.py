"""HBM-CLKLOC-3: physical DME leg failures and legal detours are memoized per site (negative cache), same results."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_trial as dt  # noqa: E402


class _Site:
    W = H = 10000.0
    forb = []

    def legal(self, q):
        return True


@pytest.fixture
def calls(monkeypatch):
    n = {"astar": 0}

    def astar(site, a, b, step=5.4, margin=600.0, turn_um=20.0):
        n["astar"] += 1
        return None if b[0] > 5000 else [tuple(a), (b[0], a[1]), tuple(b)]
    monkeypatch.setattr(dt, "legal_detour_astar", astar)
    monkeypatch.setattr(dt, "DETOUR_ADAPTIVE", False)
    monkeypatch.setattr(dt, "DME_ACTUAL_MAX_UM", 405.0)
    monkeypatch.setattr(dt, "EVEN_LEGS", False)
    return n


def test_legal_detour_memo_includes_none(calls):
    s = _Site()
    r1 = dt.legal_detour(s, (0.0, 0.0), (1000.0, 0.0))
    r2 = dt.legal_detour(s, (0.0, 0.0), (1000.0, 0.0))
    assert r1 == r2 and calls["astar"] == 1
    assert dt.legal_detour(s, (0.0, 0.0), (6000.0, 0.0)) is None
    assert dt.legal_detour(s, (0.0, 0.0), (6000.0, 0.0)) is None
    assert calls["astar"] == 2
    r2.append((9.0, 9.0))                      # callers get a copy: the memo is not mutated
    assert dt.legal_detour(s, (0.0, 0.0), (1000.0, 0.0)) == r1[:3]


def test_physical_leg_failure_is_cached(calls):
    s = _Site()
    pts = [(0.0, 0.0), (6000.0, 0.0)]           # one over-reach hop, no detour -> fails
    for _ in range(3):
        with pytest.raises(ValueError, match="no legal channel detour"):
            dt.physical_leg(s, pts[0], pts[1], 180.0, pts)
    assert calls["astar"] == 1


def test_physical_leg_success_unchanged(calls):
    s = _Site()
    pts = [(0.0, 0.0), (300.0, 0.0), (600.0, 0.0)]
    r1 = dt.physical_leg(s, pts[0], pts[-1], 180.0, pts)
    r2 = dt.physical_leg(s, pts[0], pts[-1], 180.0, pts)
    assert r1 is r2 and r1["stages"] == 2 and calls["astar"] == 0


class _SeamSite:
    """two abutting partitions x<100 and x>102 (sliver between), a keep-out wall at 200<x<300"""
    W, H = 400.0, 100.0

    def why(self, q):
        if q[0] < 1 or q[0] > 399:
            return "outside"
        if 200 < q[0] < 300:
            return "core"
        return "outside" if 100 <= q[0] <= 102 else None

    def legal(self, q):
        return self.why(q) is None


def test_seam_pass(monkeypatch):
    s = _SeamSite()
    monkeypatch.setattr(dt, "DETOUR_SEAM_PASS", False)
    assert dt.legal_detour_astar(s, (50.0, 50.0), (150.0, 50.0), step=1.0, margin=10.0) is None   # false wall
    monkeypatch.setattr(dt, "DETOUR_SEAM_PASS", True)
    assert dt.legal_detour_astar(s, (50.0, 50.0), (150.0, 50.0), step=1.0, margin=10.0) is not None
    assert dt.legal_detour_astar(s, (150.0, 50.0), (350.0, 50.0), step=1.0, margin=10.0) is None  # a real wall still blocks
    assert not dt._in_seam(s, (0.5, 50.0))                                                        # die edge is no seam
