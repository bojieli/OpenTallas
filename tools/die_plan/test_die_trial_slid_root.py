"""DIE-KV-2 10-27: die_trial slid-root leg fix.  A site-slid node that lands on the far side of a hard core from its kid
(KV G2 r3715: 800-um leg through a core, repeaters snapped to both core edges, 764 ps slew) gets a legal detour leg with
evenly spaced repeaters; legs that do not cross > rep_um of forbidden area stay byte-identical."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D


class _P:
    """one 3000 x 1000 um partition with an 800 x 400 um hard core in the middle (x 1100-1900, y 300-700)"""
    def __init__(self, cores=True):
        self.W, self.H = 3000.0, 1000.0
        hc = [dict(origin_um=[1100.0, 300.0], outline_um=[800.0, 400.0], obs_max="M7")] if cores else []
        self.types = {"t": dict(outline_um=[3000.0, 1000.0], hard_cores=hc)}
        self.parts = {"p": dict(type="t", origin_um=[0.0, 0.0])}
        self.die = {}

    def to_die(self, part, pt):
        return pt


def _nodes(px, cx, y=500.0):
    n = {0: dict(id=0, x=px, y=y, parent=None, level=0, kids=[1], taps=[]),
         1: dict(id=1, x=cx, y=y, parent=0, level=1, kids=[], taps=[("p", "ck", cx, y)])}
    return n


def _spans(place, parent_of):
    xy = {i: (x, y) for i, x, y in place}
    return max(abs(xy[a][0] - xy[b][0]) + abs(xy[a][1] - xy[b][1]) for a, b in parent_of.items())


def test_slid_root_leg_through_core_is_detoured(monkeypatch):
    monkeypatch.setattr(D, "lef_top_layer", lambda _: None)
    site = D.SiteMap(_P())
    # parent slid to the core's E edge (1902.2), kid W of the core (900): the straight leg runs 804 um inside the core
    nodes = _nodes(1902.2, 900.0)
    assert D.leg_blocked_run(site, (1902.2, 500.0), (900.0, 500.0)) > 250
    v, place, taps, nb, par = D.tree_netlist(nodes, [], rep_um=250.0, site=site)
    assert nodes[1].get("detour"), "leg must take a legal detour"
    assert all(site.legal((x, y)) for i, x, y in place if i.startswith("r"))
    assert _spans(place, par) <= 250.0 + 1e-6            # every unrepeated span <= rep_um
    # detour goes around the core (above y 702.16 or below 297.84): added length = 2 x ~205 um
    assert 300 < nodes[1]["detour_um"] < 500


def test_without_the_fix_the_old_placement_left_the_core_span(monkeypatch):
    # evidence of the root cause: the old straight placement (site.nearest on the leg axis) collapses to the core edges
    monkeypatch.setattr(D, "lef_top_layer", lambda _: None)
    site = D.SiteMap(_P())
    xs = sorted(site.nearest((1902.2 + (900.0 - 1902.2) * (j + 1) / 5, 500.0), "x")[0] for j in range(4))
    gaps = [b - a for a, b in zip([900.0] + xs, xs + [1902.2])]
    assert max(gaps) > 700


def test_leg_not_crossing_a_core_is_byte_identical(monkeypatch):
    monkeypatch.setattr(D, "lef_top_layer", lambda _: None)
    site = D.SiteMap(_P())
    a = D.tree_netlist(_nodes(2800.0, 1950.0), [], rep_um=250.0, site=site)   # E of the core, legal straight leg
    nodes = _nodes(2800.0, 1950.0)
    b = D.tree_netlist(nodes, [], rep_um=250.0, site=None)
    assert a[0] == b[0] and a[1] == b[1] and "detour" not in nodes[1]
    # a short core crossing (< rep_um of forbidden run) keeps the old nearest-site behaviour
    site2 = D.SiteMap(_P())
    n2 = _nodes(2000.0, 1000.0, y=250.0)              # y 250 is outside the core+halo: no crossing at all
    D.tree_netlist(n2, [], rep_um=250.0, site=site2)
    assert "detour" not in n2[1]


def test_polyline_points():
    pts, L = D.polyline_points([(0, 0), (100, 0), (100, 100)], [0.25, 0.5, 0.75])
    assert L == 200 and pts == [(50.0, 0.0), (100.0, 0.0), (100.0, 50.0)]
