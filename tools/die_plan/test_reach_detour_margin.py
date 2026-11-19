"""S81-CLOCK-WINDOW-1119: node 942 of the D8g S81 die clock.  A 994-um feed leg runs inside the serdes lk_ES1 PHY wall
(no legal site from y 350 to 1330 across x 26.0-29.7 mm); its bbox + 600 um ends at x 29.56 mm, short of the legal
street east of the wall, so the reach detour found no path and the kit failed closed (cw2, cw3).  The detour box now
widens in turn; the leg is re-placed on an off-path legal route with every span <= 400 um."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D

A, B = (28961.28, 339.66), (28961.28, 1333.26)


class _Site:
    """D8g geometry around node 942 (measured on the real SiteMap): legal everywhere except the die edge row y < 25,
    the PHY wall x 25990-29690 / y 340-1330 (with the parent's legal pocket at A) and a strip y 150-340 x 28500-28600."""
    W, H = 32693.76, 25980.48

    def legal(self, q):
        x, y = q
        if abs(x - A[0]) < 1.0 and abs(y - A[1]) < 1.0:
            return True
        if y < 25.0:
            return False
        if 25990.0 <= x <= 29690.0 and 340.0 <= y <= 1330.0:
            return False
        return True


def _leg():
    return dict(id=942, x=B[0], y=B[1]), dict(x=A[0], y=A[1]), [A, B]


def test_box_600_alone_finds_no_path():
    assert D.reach_detour(_Site(), A, B, 400.0, margin=600.0) is None


def test_node_942_fixed_off_path_within_reach():
    nd, p, poly = _leg()
    chain = [A, (A[0], 836.46), B]
    pts, route, info = D.reach_fix_leg(_Site(), p, nd, poly, chain, 400.0, 250.0, False)
    spans = D.chain_spans([A] + pts + [B])
    assert max(spans) <= 400.0 + 1e-6
    assert info["kind"] == "reach_detour"
    assert all(_Site().legal(q) for q in pts)
    assert max(x for x, _ in route) > 29690.0          # the route leaves the wall by the east street


def test_first_margin_unchanged(monkeypatch):
    calls = []
    real = D.reach_detour

    def spy(site, a, b, reach, **kw):
        calls.append(kw.get("margin", 600.0))
        return real(site, a, b, reach, **kw)
    monkeypatch.setattr(D, "reach_detour", spy)
    nd, p, poly = _leg()
    D.reach_fix_leg(_Site(), p, nd, poly, [A, (A[0], 836.46), B], 400.0, 250.0, False)
    assert calls[0] == 600.0 and calls == sorted(calls)


def test_no_route_anywhere_still_fails_closed():
    class Closed(_Site):
        def legal(self, q):
            return abs(q[0] - A[0]) < 1.0 and abs(q[1] - A[1]) < 1.0
    nd, p, poly = _leg()
    with pytest.raises(ValueError, match="reach_detour@4800"):
        D.reach_fix_leg(Closed(), p, nd, poly, [A, B], 400.0, 250.0, False)
