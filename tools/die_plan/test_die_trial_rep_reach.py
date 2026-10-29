"""CLK-TOOL-4 (10-29): --rep-reach-max, opt-in reach-legal placement of legs without a plan-given snake (global FEED and
plain region legs).  Root cause (S81 go16): ceil(L/rep_um)-1 evenly spaced repeaters snapped out of a hard core wider
than the reach leave one span across it (7 feed legs 457.38 um > 450), seen only by the post-build reach guard.
Default off = byte-identical; a leg whose snapped spans are all within reach is unchanged with the flag on."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D


class _P:
    """one 3000 x 1000 um partition with one hard core (x0, y0, w, h)"""
    def __init__(self, core=(1100.0, 300.0, 457.0, 400.0)):
        self.W, self.H = 3000.0, 1000.0
        x, y, w, h = core
        self.types = {"t": dict(outline_um=[3000.0, 1000.0],
                                hard_cores=[dict(origin_um=[x, y], outline_um=[w, h], obs_max="M7")])}
        self.parts = {"p": dict(type="t", origin_um=[0.0, 0.0])}
        self.die = {}

    def to_die(self, part, pt):
        return pt


def _nodes(px, cx, y=500.0, feed=True):
    return {0: dict(id=0, x=px, y=y, parent=None, level=0, kids=[1], taps=[], feed=feed),
            1: dict(id=1, x=cx, y=y, parent=0, level=1, kids=[], taps=[("p", "ck", cx, y)], feed=feed)}


def _spans(place, parent_of):
    xy = {i: (x, y) for i, x, y in place}
    return max(abs(xy[a][0] - xy[b][0]) + abs(xy[a][1] - xy[b][1]) for a, b in parent_of.items())


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.setattr(D, "lef_top_layer", lambda _: None)
    yield
    D.REP_REACH_MAX_UM = None
    D.REP_ON_LEG = False


def test_stock_feed_leg_leaves_the_core_span():
    # the S81 go16 failure: 760-um feed leg, 3 repeaters, core 461.3 um wide incl halo -> one span > 450
    site = D.SiteMap(_P())
    _, place, _, _, par = D.tree_netlist(_nodes(1000.0, 1760.0), [], rep_um=250.0, site=site)
    assert _spans(place, par) > 450.0


def test_reach_detour_feed_leg_meets_reach_and_records_cost():
    D.REP_REACH_MAX_UM = 450.0
    site = D.SiteMap(_P())
    n = _nodes(1000.0, 1760.0)
    _, place, _, _, par = D.tree_netlist(n, [], rep_um=250.0, site=site)
    reps = [(x, y) for i, x, y in place if i.startswith("r")]
    assert all(site.legal(c) for c in reps)
    assert _spans(place, par) <= 450.0 + 1e-6
    rf = n[1]["reach_fix"]
    assert rf["kind"] == "reach_detour" and rf["span_before_um"] > 450.0 >= rf["span_after_um"]
    # around the core (top halo 702.16 / bottom 297.84 from y 500): ~2 x 202 um added, priced and recorded
    assert 380.0 < rf["added_wire_um"] < 520.0 and n[1]["detour_um"] == pytest.approx(rf["added_wire_um"], abs=0.1)
    assert rf["nrep_after"] == len(reps) and rf["added_stages"] == len(reps) - 3


def test_on_path_fix_adds_repeaters_without_wire():
    # no core on the leg; rep_um 600 -> 1 repeater, span 500 > reach 450: on-path re-placement, no added wire
    D.REP_REACH_MAX_UM = 450.0
    site = D.SiteMap(_P(core=(2900.0, 900.0, 50.0, 50.0)))
    n = _nodes(100.0, 1100.0, y=200.0)
    _, place, _, _, par = D.tree_netlist(n, [], rep_um=600.0, site=site)
    rf = n[1]["reach_fix"]
    assert rf["kind"] == "on_path" and rf["added_wire_um"] == 0.0 and rf["nrep_after"] == 2
    assert _spans(place, par) <= 450.0 + 1e-6 and all(abs(y - 200.0) < 1e-6 for i, x, y in place)
    assert "detour" not in n[1]


def test_inv2_keeps_even_stage_count():
    D.REP_REACH_MAX_UM = 450.0
    site = D.SiteMap(_P(core=(2900.0, 900.0, 50.0, 50.0)))
    n = _nodes(100.0, 1100.0, y=200.0)
    v, place, _, _, par = D.tree_netlist(n, [], rep_um=600.0, site=site, clock_cell="inv2")
    rf = n[1]["reach_fix"]
    assert (rf["nrep_after"] + 1) % 2 == 0 and rf["nrep_after"] == 3
    assert n[1]["inv_parity"] == 0 and _spans(place, par) <= 450.0 + 1e-6


def test_no_legal_placement_fails_closed():
    # a full-height core 500 um wide: no on-path placement and no detour inside the die -> the kit fails
    D.REP_REACH_MAX_UM = 450.0
    site = D.SiteMap(_P(core=(1100.0, 0.0, 500.0, 1000.0)))
    with pytest.raises(ValueError, match="rep-reach-max 450: leg to node 1"):
        D.tree_netlist(_nodes(1000.0, 1760.0), [], rep_um=250.0, site=site)


def test_default_and_in_reach_legs_are_byte_identical():
    a = D.tree_netlist(_nodes(1000.0, 1760.0), [], rep_um=250.0, site=D.SiteMap(_P()))
    b = D.tree_netlist(_nodes(1000.0, 1760.0, y=850.0), [], rep_um=250.0, site=D.SiteMap(_P()))
    D.REP_REACH_MAX_UM = 470.0          # the 462-um span is within this reach: unchanged
    c = D.tree_netlist(_nodes(1000.0, 1760.0), [], rep_um=250.0, site=D.SiteMap(_P()))
    D.REP_REACH_MAX_UM = 450.0          # a leg clear of the core: unchanged
    d = D.tree_netlist(_nodes(1000.0, 1760.0, y=850.0), [], rep_um=250.0, site=D.SiteMap(_P()))
    assert a[:2] == c[:2] and b[:2] == d[:2]


def test_reach_place_minimises_the_largest_span():
    class S:
        def legal(self, q):
            return not (300.0 < q[0] < 700.0)
    q = D.reach_place(S(), [(0.0, 0.0), (1000.0, 0.0)], 450.0)
    ch = [0.0] + [x for x, _ in q] + [1000.0]
    assert len(q) == 2 and max(b - a for a, b in zip(ch, ch[1:])) <= 450.0
    assert D.reach_place(S(), [(0.0, 0.0), (1000.0, 0.0)], 390.0) is None


def _two(feed=True):
    """root at (1000, 500) with kid 1 across the core (E, x 1760) and kid 2 clear of it (W, x 240), both with taps"""
    return {0: dict(id=0, x=1000.0, y=500.0, parent=None, level=0, kids=[1, 2], taps=[], feed=feed),
            1: dict(id=1, x=1760.0, y=500.0, parent=0, level=1, kids=[], taps=[("p", "a", 1760.0, 500.0)], feed=feed),
            2: dict(id=2, x=240.0, y=500.0, parent=0, level=1, kids=[], taps=[("p", "b", 240.0, 500.0)], feed=feed)}


def _arrivals(place, parent_of, nodes):
    xy = {i: (x, y) for i, x, y in place}
    out = {}
    for k in (1, 2):
        path, c = [], f"b{k}"
        while c in parent_of:
            path.append(xy[c])
            c = parent_of[c]
        path.append(xy[c])
        out[k] = D.chain_ps(list(reversed(path)))
    return out


def test_balance_pads_the_sibling_by_the_priced_reach_delay():
    D.REP_REACH_MAX_UM = 450.0
    site = D.SiteMap(_P())
    base = _two()
    D.REP_REACH_MAX_UM = None
    _, p0, _, _, par0 = D.tree_netlist(base, [], rep_um=250.0, site=D.SiteMap(_P()))
    a0 = _arrivals(p0, par0, base)
    D.REP_REACH_MAX_UM = 450.0
    n = _two()
    _, place, _, _, par = D.tree_netlist(n, [], rep_um=250.0, site=site)
    a1 = _arrivals(place, par, n)
    d = n[1]["reach_fix"]["added_ps_model"]
    assert d > 0 and a1[1] - a0[1] == pytest.approx(d, abs=0.01)
    bal = n[0]["reach_balance"]
    assert bal["fixed_legs"] == 1 and bal["pads"] == 1 and n[2].get("reach_pad")
    # relative arrival kid1 - kid2 kept within the snake delay quantum (residual recorded)
    assert abs((a1[1] - a1[2]) - (a0[1] - a0[2])) <= max(2.0, bal["residual_max_ps"] + 0.6)
    assert _spans(place, par) <= 450.0 + 1e-6


def test_no_balance_flag_leaves_siblings_unpadded():
    D.REP_REACH_MAX_UM = 450.0
    D.REP_REACH_BALANCE = False
    try:
        n = _two()
        D.tree_netlist(n, [], rep_um=250.0, site=D.SiteMap(_P()))
        assert n[1].get("reach_fix") and not n[2].get("snake") and "reach_balance" not in n[0]
    finally:
        D.REP_REACH_BALANCE = True
