"""HBM-CLKLOC-6: opt-in --region-dme-split REG:K (K equal-count sub-regions per partition along the long axis, one DME
tree each, joined at the region merge) and --region-dme-street-pair REGIONS (adjacent streets share one rib column);
both default off (trees unchanged)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D
from test_die_trial_region_dme_early import _arrivals
from test_die_trial_slice_spine import FakeSite
from test_die_trial_region_dme_street import _region


def _tall():
    """one tall partition (300 x 4000 um, as HBM T010 'root'), 40 taps on 2 columns"""
    site = FakeSite(400.0, 4000.0, [])
    taps = [("root", f"clk_{c}{i}", 100.0 + 150.0 * c, 50.0 + 100.0 * i) for c in (0, 1) for i in range(20)]
    return site, taps


def test_split_default_off_unchanged():
    site, taps = _tall()
    a = D.dme_region_tree(site, taps, delay_rep_um=250.0)
    b = D.dme_region_tree(site, taps, delay_rep_um=250.0, split=None)
    c = D.dme_region_tree(site, taps, delay_rep_um=250.0, split=1)
    assert a == b == c


def test_split_two_halves_along_long_axis():
    site, taps = _tall()
    dn, root, st = D.dme_region_tree(site, taps, delay_rep_um=250.0, split=2)
    a = _arrivals(dn, root, 250.0)
    assert sorted(a) == sorted(t[1] for t in taps)                # every tap delivered once
    assert max(a.values()) - min(a.values()) < 5.0                # balanced by construction (model)
    proots = {d["part_root"]: d for d in dn if d.get("part_root")}
    assert set(proots) == {"root#s0", "root#s1"}                  # one sub-region tree per half
    ys = {}
    st_ = list(proots.items())
    for name, d0 in st_:                                          # taps under each sub-root: one y half each
        idx = dn.index(d0)
        stack, yy = [idx], []
        while stack:
            i = stack.pop()
            yy += [t[3] for t in dn[i]["taps"]]
            stack += dn[i]["kids"]
        ys[name] = yy
    assert len(ys["root#s0"]) == len(ys["root#s1"]) == 20
    assert max(ys["root#s0"]) < min(ys["root#s1"])


def test_street_pair_shares_one_column(monkeypatch):
    monkeypatch.setattr(D, "DME_STREET_COLUMN", True)
    monkeypatch.setattr(D, "DME_STREET_VGAPS", None)
    site = FakeSite(1600.0, 4000.0, [])
    # 4 streets 170 um apart (gap 120 -> 4 streets); pairs (0,1) and (2,3) share one column each
    taps = [("p", f"clk_{s}_{i}", 200.0 + 170.0 * s, 300.0 + 400.0 * i) for s in range(4) for i in range(5)]
    one = D._street_columns(site, taps, lambda t: (t[2], t[3]), 120.0)
    two = D._street_columns(site, taps, lambda t: (t[2], t[3]), 120.0, pair=True)
    assert len({q[0] for q in one.values()}) == 4
    cols = sorted({q[0] for q in two.values()})
    assert cols == [285.0, 625.0]                                  # midway between the paired streets
    assert all(q[1] == t[3] for t in taps for q in [two[(t[0], t[1])]])
    assert D._street_columns(site, taps, lambda t: (t[2], t[3]), 120.0, pair=False) == one


def test_street_pair_tree_balanced(monkeypatch):
    monkeypatch.setattr(D, "DME_STREET_COLUMN", True)
    monkeypatch.setattr(D, "DME_STREET_VGAPS", None)
    site, taps = _region()
    dn, root, st = D.dme_region_tree(site, taps, delay_rep_um=250.0, street=True, street_pair=True)
    a = _arrivals(dn, root, 250.0)
    assert sorted(a) == sorted(t[1] for t in taps)
    assert max(a.values()) - min(a.values()) < 5.0


def test_vgap_snap_moves_drivers_and_merges_onto_gaps(monkeypatch):
    """--region-dme-vgap: every driver / merge point on a PG-free gap centre (vertical runs in a gap); off = unchanged"""
    gaps = [25.92 + 17.28 * k for k in range(22)]
    monkeypatch.setattr(D, "DME_STREET_VGAPS", gaps)
    site, taps = _tall()
    a = D.dme_region_tree(site, taps, delay_rep_um=250.0)
    assert a == D.dme_region_tree(site, taps, delay_rep_um=250.0, vgap=False)
    dn, root, st = D.dme_region_tree(site, taps, delay_rep_um=250.0, vgap=True)
    arr = _arrivals(dn, root, 250.0)
    assert sorted(arr) == sorted(t[1] for t in taps)
    assert max(arr.values()) - min(arr.values()) < 10.0
    for d in dn:
        assert any(abs(d["x"] - g) < 1e-6 for g in gaps), d["x"]
        assert site.legal((d["x"], d["y"]))


def test_vgap_snap_keeps_point_when_no_legal_gap():
    site = FakeSite(400.0, 400.0, [(0.0, 0.0, 400.0, 190.0)])      # a core covering y < 190
    D_gaps = D.DME_STREET_VGAPS
    try:
        D.DME_STREET_VGAPS = [25.92, 43.2]
        assert D._vgap_snap(site, (30.0, 100.0)) == (30.0, 100.0)  # gap site illegal (core) -> unchanged
        assert D._vgap_snap(site, (30.0, 300.0)) == (25.92, 300.0)
        assert D._vgap_snap(site, (300.0, 300.0)) == (300.0, 300.0)  # farther than one pitch -> unchanged
    finally:
        D.DME_STREET_VGAPS = D_gaps
