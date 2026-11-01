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
    def chan(q):
        return 1950.0 <= q[1] <= 2050.0

    def street(q):
        return min((400.0, 800.0, 1200.0), key=lambda s_: abs(s_ - q[0])) if abs(q[0] - _street_of(q[0])) <= 40.0 else None
    spine = 0
    for p, q in _legs(dn, root):
        if chan(p) and chan(q):
            spine += street(p) != street(q) or street(p) is None   # spine leg: runs in the mid channel
            continue
        # rib leg (at least one end off the channel): both ends inside the same street, so no leg crosses a core
        assert street(p) is not None and street(p) == street(q), (p, q)
    assert spine >= 2                                             # 3 streets -> at least 2 spine merges
    for d in dn:                                                  # every node legal (streets / channel)
        assert site.legal((d["x"], d["y"]))


def test_street_off_is_default_and_unchanged():
    site, taps = _region()
    assert D.DME_STREET is None
    a = D.dme_region_tree(site, taps, delay_rep_um=250.0)
    b = D.dme_region_tree(site, taps, delay_rep_um=250.0, street=False)
    assert a == b and "street" not in a[2]["topology"]


def test_streets_cluster_on_driver_point_not_core_pin():
    """tap pins 120 um from the street centre, inside the cores (as HBM SM core clock pins): raw pin x splits each
    street in two (gap 240 > 200); the legal driver points sit in the street -> one rib per street, spine in the channel"""
    site, taps = _region()
    deep = [(p, n, x + (-80.0 if x < _street_of(x) else 80.0), y) for p, n, x, y in taps]
    deep.append(("core1", "clk_chan", 420.0, 2000.0))          # an odd tap in the channel next to street 400
    dn, root, st = D.dme_region_tree(site, deep, delay_rep_um=250.0, street=True)
    a = _arrivals(dn, root, 250.0)
    assert len(a) == len(deep)
    for p, q in _legs(dn, root):                               # every leg has an L route on legal sites (no core)
        assert any(_clear(site, p, c, q) for c in ((p[0], q[1]), (q[0], p[1]))), (p, q)


def _clear(site, p, c, q, step=5.0):
    for u, v in ((p, c), (c, q)):
        n = int(max(abs(u[0] - v[0]), abs(u[1] - v[1])) / step) + 1
        for i in range(n + 1):
            if not site.legal((u[0] + (v[0] - u[0]) * i / n, u[1] + (v[1] - u[1]) * i / n)):
                return False
    return True


def test_street_column_on_pg_free_gap(monkeypatch):
    """--region-dme-street-column (+ -vlayer): all drivers of a street on one column x, at a PG-free gap centre"""
    from types import SimpleNamespace
    P = SimpleNamespace(W=1600.0, H=4000.0, layers={"M9": {"dir": "V"}, "M8": {"dir": "H"}},
                        die={"pg": {"grid": [{"layer": "M9", "width_um": 12.96, "pitch_um": 34.56, "offset_um": 17.28,
                                               "nets": ["VDD", "VSS"]},
                                              {"layer": "M8", "width_um": 0.48, "pitch_um": 4.32, "offset_um": 2.16}]}})
    gaps = D.street_vgaps(P, "M9")
    assert gaps[:2] == [25.92, 43.2] and all(abs(b - a - 17.28) < 1e-6 for a, b in zip(gaps, gaps[1:]))
    monkeypatch.setattr(D, "DME_STREET_COLUMN", True)
    monkeypatch.setattr(D, "DME_STREET_VGAPS", gaps)
    site, taps = _region()
    dn, root, st = D.dme_region_tree(site, taps, delay_rep_um=250.0, street=True)
    assert len(_arrivals(dn, root, 250.0)) == len(taps)
    for d in dn:
        if d["taps"]:
            x = d["x"]
            assert any(abs(x - g) < 1e-6 for g in gaps), x                # driver on a gap centre
    cols = {round(d["x"], 3) for d in dn if d["taps"]}
    assert len(cols) == 3                                                  # one column per street


def test_street_column_keeps_far_taps_on_their_own_point(monkeypatch):
    """a wide cluster (taps spread 0..600 um at < gap spacing, no street): taps more than gap/2 from the column keep
    their own driver point, so no tap edge outgrows the reach"""
    monkeypatch.setattr(D, "DME_STREET_COLUMN", True)
    monkeypatch.setattr(D, "DME_STREET_VGAPS", None)
    site = FakeSite(1600.0, 4000.0, [])
    taps = [("p", f"clk_{i}", 100.0 + 150.0 * i, 500.0 + 300.0 * i) for i in range(5)]   # x 100..700, one cluster
    drv = D._street_columns(site, taps, lambda t: (t[2], t[3]), 200.0)
    for t in taps:
        q = drv[(t[0], t[1])]
        assert abs(q[0] - t[2]) <= 100.0 and q[1] == t[3]
    assert sum(drv[(t[0], t[1])] == (t[2], t[3]) for t in taps) >= 2      # the far ends keep their own point


def test_gap_column_snake_stays_in_pg_free_gaps(monkeypatch):
    """HBM-CLKLOC-5: with -vlayer, a snake on a vertical rib leg that runs on a gap centre keeps every buffer inside a
    PG-free gap (C9d T002: a 20.7-um dogleg jog put the rib under an M9 stripe -> M7, +194 ps); other legs unchanged"""
    from types import SimpleNamespace
    P = SimpleNamespace(W=1600.0, H=4000.0, layers={"M9": {"dir": "V"}},
                        die={"pg": {"grid": [{"layer": "M9", "width_um": 12.96, "pitch_um": 34.56, "offset_um": 17.28,
                                               "nets": ["VDD", "VSS"]}]}})
    gaps = D.street_vgaps(P, "M9")
    assert D.street_vgap_half(P, "M9") == 2.16
    monkeypatch.setattr(D, "DME_STREET_VGAPS", gaps)
    monkeypatch.setattr(D, "DME_STREET_VGAP_HALF", 2.16)
    c = gaps[20]
    assert D.snake_leaves_vgap((c, 100.0), (c, 1500.0), [(c, 100.0), (c + 20.7, 700.0), (c, 1500.0)])
    assert not D.snake_leaves_vgap((c, 100.0), (c, 1500.0), [(c, 100.0), (c + 17.28, 700.0), (c, 1500.0)])
    assert not D.snake_leaves_vgap((c + 9.0, 100.0), (c + 9.0, 1500.0), [(c + 30.0, 700.0)])     # not a gap column
    assert not D.snake_leaves_vgap((c, 100.0), (c + 200.0, 1500.0), [(c + 20.7, 700.0)])        # not vertical
    site = FakeSite(1600.0, 4000.0, [])
    pa, q = (c, 100.0), (c, 1500.0)
    plain = D.placed_leg_ps(site, pa, q, 250.0)
    r = D.snake_leg(site, pa, q, plain + 6.0, 250.0)
    if r is not None:
        assert not D.snake_leaves_vgap(pa, q, [pa] + [tuple(x) for x in r[0]] + [q])
    monkeypatch.setattr(D, "DME_STREET_COL_SNAKE", "same")
    assert D.snake_leaves_vgap((c, 100.0), (c, 1500.0), [(c, 100.0), (c + 17.28, 700.0), (c, 1500.0)])
    assert not D.snake_leaves_vgap((c, 100.0), (c, 1500.0), [(c, 100.0), (c + 1.0, 1700.0), (c, 1500.0)])
    monkeypatch.setattr(D, "DME_STREET_COL_SNAKE", "off")
    assert D.snake_leaves_vgap((c, 100.0), (c, 1500.0), [(c, 100.0), (c, 1500.0)])
    assert D.snake_leg(site, pa, q, plain + 6.0, 250.0) is None
    monkeypatch.setattr(D, "DME_STREET_COL_SNAKE", "gap")
    monkeypatch.setattr(D, "DME_STREET_VGAPS", None)
    r0 = D.snake_leg(site, pa, q, plain + 6.0, 250.0)
    assert r0 is not None                                                  # guard off: unchanged search
