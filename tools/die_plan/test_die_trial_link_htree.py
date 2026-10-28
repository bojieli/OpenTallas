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


class _Site:
    """legal everywhere except a 300 x 300 um block around the region-A centre (1000, 200)"""
    W, H = 3000.0, 400.0

    def legal(self, q):
        return not (850 < q[0] < 1150 and 50 < q[1] < 350)

    def hits(self, q):
        return [] if self.legal(q) else [(850.0, 50.0, 1150.0, 350.0, "core")]

    def nearest(self, p, axis=None):
        if self.legal(p):
            return tuple(p)
        return min(((850.0, p[1]), (1150.0, p[1]), (p[0], 50.0), (p[0], 350.0)),
                   key=lambda c: abs(c[0] - p[0]) + abs(c[1] - p[1]))


def test_balance_legalize_keeps_region_balanced():
    n = D.build_link_fishbone(_P(), TAPS, REG, FEED, local="htree", leaf_um=200.0)
    for d in n.values():
        d["req_xy"] = [d["x"], d["y"]]
    st = D.balance_legalize(n, _Site())
    assert st["unbalanced"] == 0 and st["moved"] >= 1
    site = _Site()
    for d in n.values():
        if d.get("rib") is not None or d.get("region_root") is not None:
            assert site.legal((d["x"], d["y"]))
    # region A: every root->tap wire length (legs + last mile) equal within tol where the leaves hold one tap
    rr = next(i for i, d in n.items() if d.get("region_root") == "A")
    tot = []
    for i, d in n.items():
        if d["taps"] and REG[d["taps"][0][0]] == "A":
            L, j = abs(d["taps"][0][2] - d["x"]) + abs(d["taps"][0][3] - d["y"]), i
            while j != rr:
                p = n[n[j]["parent"]]
                L += abs(p["x"] - n[j]["x"]) + abs(p["y"] - n[j]["y"])
                j = n[j]["parent"]
            tot.append(L)
    assert max(tot) - min(tot) <= 2.0 * 4 + 1e-6, tot



def test_link_htree_full_keeps_empty_halves():
    n = D.build_link_fishbone(_P(), TAPS, REG, FEED, local="htree", leaf_um=200.0, full=1.0)
    lf = n[0]["link_feed"]
    assert lf["full"] and lf["tapless_leaves"] > 0
    for i, d in n.items():
        if d.get("rib") is not None and d["kids"]:
            assert len(d["kids"]) == 2
