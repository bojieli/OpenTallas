"""DIE-QC-13: --tree-opt region_stub=1 (opt-in).  The feed end of every region that feeds other regions becomes a shared
feed node: the region own tree hangs from a stub node at the same point, so the shared node carries no region taps
(reset-release start ports leave the fork as a retime flop, 12.16b(iv)).  Leaf regions and the default are unchanged."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D
from test_die_trial_link_fishbone import _P, REG, FEED
from test_die_trial_link_htree import TAPS


def _build(**kw):
    return D.build_link_fishbone(_P(), TAPS, REG, FEED, local="htree", leaf_um=200.0, **kw)


def test_default_unchanged():
    assert _build() == _build(region_stub=0.0)


def test_feed_parents_get_stub():
    n = _build(region_stub=1.0)
    parents = {p for p in FEED["parent"].values() if p is not None}
    assert parents
    for r in set(REG.values()):
        roots = [i for i, d in n.items() if d.get("region_root") == r]
        assert len(roots) == 1
        d = n[roots[0]]
        if r in parents:
            s = n[d["parent"]]
            assert d.get("region_stub") and s.get("shared_feed") == r
            assert (s["x"], s["y"]) == (d["x"], d["y"]) and not s["taps"]
            # the shared node feeds the child regions and the stub; the region taps all hang below the stub
            kid_roots = {n[k].get("region_root") for k in s["kids"]}
            assert None in kid_roots or kid_roots & set(REG.values())
        else:
            assert not d.get("region_stub")


def test_taps_and_regions_preserved():
    a, b = _build(), _build(region_stub=1.0)
    ta = sorted(t for d in a.values() for t in d["taps"])
    tb = sorted(t for d in b.values() for t in d["taps"])
    assert ta == tb
    parents = {p for p in FEED["parent"].values() if p is not None}
    assert len(b) == len(a) + len(parents)


def test_inv2_netlist_even_polarity():
    n = _build(region_stub=1.0)
    for i, d in n.items():
        d.setdefault("x", d["x"])
    v = D.tree_netlist(n, TAPS, rep_um=250.0, clock_cell="inv2")
    assert v and all(d["inv_parity"] == 0 for d in n.values())
