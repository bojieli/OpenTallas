"""DIE-KV-3 10-27: die_trial --tree-form link_htree.  Region clocks follow the locality feed tree (as link_fishbone); inside
each region a BALANCED H-tree (full-depth bisection to leaf_um, child at the child box centre): every root->leaf path of a
region has the same leg lengths, so the nominal in-region skew is the last-mile leg only."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D
from test_die_trial_link_fishbone import _P, REG, FEED

TAPS = [("a0", "ck", 100.0, 50.0), ("a0", "ck2", 900.0, 350.0), ("a1", "ck", 1500.0, 100.0), ("a1", "ck2", 1950.0, 380.0),
        ("b0", "ck", 2500.0, 200.0)]


def _path_legs(n, i):
    legs = []
    while n[i]["parent"] is not None:
        p = n[n[i]["parent"]]
        legs.append(abs(p["x"] - n[i]["x"]) + abs(p["y"] - n[i]["y"]))
        i = n[i]["parent"]
    return legs


def test_link_htree_balanced_per_region():
    n = D.build_link_fishbone(_P(), TAPS, REG, FEED, local="htree", leaf_um=200.0)
    assert n[0]["link_feed"]["local"] == "htree" and n[0]["link_feed"]["feed_wire_um"] == 1500.0
    got = sorted(t[0] + t[1] for d in n.values() for t in d["taps"])
    assert got == sorted(t[0] + t[1] for t in TAPS)
    for r in ("A", "B"):
        rr = next(i for i, d in n.items() if d.get("region_root") == r)
        leaves = [i for i, d in n.items() if d["taps"] and REG[d["taps"][0][0]] == r]
        # path from the region root to each leaf: identical leg-length sequence (balanced by construction)
        seqs = set()
        for lf in leaves:
            legs, i = [], lf
            while i != rr:
                p = n[n[i]["parent"]]
                legs.append(round(abs(p["x"] - n[i]["x"]) + abs(p["y"] - n[i]["y"]), 3))
                i = n[i]["parent"]
            seqs.add(tuple(legs))
            # leaf box <= leaf_um, last-mile leg <= leaf_um
            for t in n[lf]["taps"]:
                assert abs(t[2] - n[lf]["x"]) + abs(t[3] - n[lf]["y"]) <= 200.0 + 1e-6
        assert len(seqs) == 1, (r, seqs)
    for i, d in n.items():
        if d["parent"] is not None:
            p = n[d["parent"]]
            assert abs(p["x"] - d["x"]) < 1e-6 or abs(p["y"] - d["y"]) < 1e-6


def test_link_fishbone_default_unchanged():
    a = D.build_link_fishbone(_P(), TAPS, REG, FEED)
    b = D.build_link_fishbone(_P(), TAPS, REG, FEED, local="fishbone", leaf_um=123.0)
    assert a == b and "local" not in a[0]["link_feed"]
