"""HBM-CLKLOC-2: --region-dme-physical-topk must never fail a merge the full-pool rule would place."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_trial as dt  # noqa: E402


class _Site:
    W = H = 10000.0

    def legal(self, q):
        return True


@pytest.fixture
def phys(monkeypatch):
    monkeypatch.setattr(dt, "DME_ACTUAL_MAX_UM", 405.0)
    monkeypatch.setattr(dt, "DME_PHYS_TOPK", 2)
    monkeypatch.setattr(dt, "merge_point", lambda site, c1, d1, c2, d2, r, s, t: ((500.0, 0.0), 0, 0))
    return monkeypatch


def _only_reachable(ok):
    def leg(site, a, b, rep_um, par):
        if not ok(a):
            raise ValueError("no legal channel detour")
        return dt._man(a, b) * 0.3
    return leg


def test_topk_falls_back_to_rest_of_pool(phys):
    # every point near the length solution (the fast-ranked top K) is unreachable; only far path points remain
    phys.setattr(dt, "_par_leg_ps", _only_reachable(lambda q: abs(q[0] - 500.0) > 100.0))
    q, imb, extra = dt.merge_point_delay(_Site(), (0.0, 0.0), 0.0, (1000.0, 0.0), 0.0, 180.0)
    assert abs(q[0] - 500.0) > 100.0


def test_topk_still_raises_when_nothing_reachable(phys):
    phys.setattr(dt, "_par_leg_ps", _only_reachable(lambda q: False))
    with pytest.raises(ValueError, match="no reachable physical DME merge candidate"):
        dt.merge_point_delay(_Site(), (0.0, 0.0), 0.0, (1000.0, 0.0), 0.0, 180.0)


def test_topk_keeps_fast_choice_when_reachable(phys):
    phys.setattr(dt, "_par_leg_ps", _only_reachable(lambda q: True))
    q, imb, extra = dt.merge_point_delay(_Site(), (0.0, 0.0), 0.0, (1000.0, 0.0), 0.0, 180.0)
    assert imb < 1.0
