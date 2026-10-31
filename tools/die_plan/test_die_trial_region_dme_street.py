"""HBM-CLKLOC-4: --region-dme-street opt-in street-region (fishbone) DME form: one balanced rib per street, spine of
x cuts between streets; partitions ignored; default (street off) unchanged."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D
from test_die_trial_region_dme_early import _arrivals
from test_die_trial_slice_spine import FakeSite

# an SM-like region: two rows of tall cores (y 50..1950 and 2050..3950), 80-um streets between them at x = 400 k,
# a 100-um mid channel at y 1950..2050; taps on the core edges facing the streets (both sides of a street)
CORES = [(x0 + 40.0, y0, x0 + 360.0, y1) for x0 in (0.0, 400.0, 800.0, 1200.0)
         for (y0, y1) in ((50.0, 1950.0), (2050.0, 3950.0))]


def _region():
    site = FakeSite(1600.0, 4000.0, CORES)
    taps = []
    for k, sx in enumerate((400.0, 800.0, 1200.0)):
        for side, dx in (("w", -40.0), ("e", 40.0)):
            for ty in (500.0, 1500.0, 2500.0, 3500.0):
                # partitions = cores, so a core's taps sit in two different streets (as on HBM SM cores)
                taps.append((f"core{k + (side == 'e')}", f"clk_{k}{side}{int(ty)}", sx + dx, ty))
    return site, taps


def _legs(dn, root):
    st, out = [root], []
    while st:
        i = st.pop()
        for k in dn[i]["kids"]:
            out.append(((dn[i]["x"], dn[i]["y"]), (dn[k]["x"], dn[k]["y"])))
            st.append(k)
    return out


def _street_of(x):
    return min((400.0, 800.0, 1200.0), key=lambda s: abs(s - x))


def test_street_cut_never_splits_a_street():
    pts = [(400.0 + dx, y) for dx in (-40.0, 40.0) for y in (500.0, 1500.0, 2500.0, 3500.0)] + \
          [(800.0 + dx, y) for dx in (-40.0, 40.0) for y in (500.0, 1500.0)]
    l, r = D._street_cut(pts, 200.0)
    assert {_street_of(pts[i][0]) for i in l} == {400.0} and {_street_of(pts[i][0]) for i in r} == {800.0}
    one = [(400.0, y) for y in (3500.0, 500.0, 2500.0, 1500.0)]
    l, r = D._street_cut(one, 200.0)                       # inside one street: y median (rib)
    assert sorted(one[i][1] for i in l) == [500.0, 1500.0] and sorted(one[i][1] for i in r) == [2500.0, 3500.0]


def test_street_form_ribs_and_spine():
    site, taps = _region()
    dn, root, st = D.dme_region_tree(site, taps, delay_rep_um=250.0, street=True)
    assert st["topology"] == {"street": 1}
    a = _arrivals(dn, root, 250.0)
    assert sorted(a) == sorted(t[1] for t in taps)               # every tap delivered once
    assert max(a.values()) - min(a.values()) < 5.0               # balanced by construction (model)
    for p, q in _legs(dn, root):
        if abs(p[0] - q[0]) > 1.0:                                # a cross-street leg = spine: in the mid channel
            assert 1950.0 <= p[1] <= 2050.0 and 1950.0 <= q[1] <= 2050.0, (p, q)
        else:                                                     # a rib leg: inside one street
            assert _street_of(p[0]) == _street_of(q[0])
    for d in dn:                                                  # every node legal (streets / channel)
        assert site.legal((d["x"], d["y"]))


def test_street_off_is_default_and_unchanged():
    site, taps = _region()
    assert D.DME_STREET is None
    a = D.dme_region_tree(site, taps, delay_rep_um=250.0)
    b = D.dme_region_tree(site, taps, delay_rep_um=250.0, street=False)
    assert a == b and "street" not in a[2]["topology"]
