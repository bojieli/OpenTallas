"""DIE-KV-2 10-27: die_trial --tree-form link_fishbone.  Region clocks follow the locality feed tree (centre -> link tap ->
centre, straight legs), each region a fishbone (trunk on the long axis, one node per tap column, stub per tap row)."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D


class _P:
    """three 1000 x 400 um partitions in a row; regions A = {a0, a1}, B = {b0}"""
    def __init__(self):
        self.W, self.H = 3000.0, 400.0
        self.types = {"t": dict(outline_um=[1000.0, 400.0])}
        self.parts = {n: dict(type="t", origin_um=[x, 0.0]) for n, x in (("a0", 0.0), ("a1", 1000.0), ("b0", 2000.0))}


TAPS = [("a0", "ck", 500.0, 200.0), ("a1", "ck", 1500.0, 100.0), ("b0", "ck", 2500.0, 200.0)]
REG = {"a0": "A", "a1": "A", "b0": "B"}
FEED = {"root": "A", "parent": {"A": None, "B": "A"}, "tap": {"A->B": [2000.0, 200.0]}}


def test_feed_follows_link_and_fishbone():
    n = D.build_link_fishbone(_P(), TAPS, REG, FEED)
    root = n[0]
    assert (root["x"], root["y"]) == (1000.0, 200.0) and root["region_root"] == "A"
    rb = [i for i, d in n.items() if d.get("region_root") == "B"]
    assert len(rb) == 1 and (n[rb[0]]["x"], n[rb[0]]["y"]) == (2500.0, 200.0)
    # B is fed from the A centre through the link tap: feed wire = |1000-2000| + |2000-2500|
    assert n[0]["link_feed"] == dict(root="A", regions=2, feed_edges=1, feed_wire_um=1500.0)
    # every leg straight (axis-aligned)
    for i, d in n.items():
        if d["parent"] is not None:
            p = n[d["parent"]]
            assert abs(p["x"] - d["x"]) < 1e-6 or abs(p["y"] - d["y"]) < 1e-6
    # each tap attached exactly once; a1 (100 um off the trunk, > col_um) gets its own stub leaf
    got = sorted(t[0] for d in n.values() for t in d["taps"])
    assert got == ["a0", "a1", "b0"]
    leaf_a1 = next(d for d in n.values() if any(t[0] == "a1" for t in d["taps"]))
    assert (leaf_a1["x"], leaf_a1["y"]) == (1500.0, 100.0) and n[leaf_a1["parent"]]["y"] == 200.0


def test_region_missing_from_feed_is_an_error():
    import pytest
    with pytest.raises(SystemExit):
        D.build_link_fishbone(_P(), TAPS, REG, {"root": "A", "parent": {"A": None}, "tap": {}})


def _anc(n, i):
    out = []
    while i is not None:
        out.append(i)
        i = n[i]["parent"]
    return out


def _len(n, i):
    L = 0.0
    while n[i]["parent"] is not None:
        p = n[n[i]["parent"]]
        L += abs(p["x"] - n[i]["x"]) + abs(p["y"] - n[i]["y"])
        i = n[i]["parent"]
    return L


def test_region_htree_balanced():
    """DIE-S81-3 region_tree=htree: same feed, balanced local tree per region: every tap once, legs straight, and every
    leaf of a region at the same root->leaf length (zero nominal in-region skew up to the <= leaf_um last mile)"""
    taps = TAPS + [("a0", "ck2", 100.0, 350.0), ("a1", "ck2", 1900.0, 50.0), ("b0", "ck2", 2900.0, 380.0)]
    n = D.build_link_fishbone(_P(), taps, REG, FEED, region_tree="htree", leaf_um=150.0)
    assert sorted(t for d in n.values() for t in d["taps"]) == sorted(taps)
    for i, d in n.items():
        if d["parent"] is not None:
            p = n[d["parent"]]
            assert abs(p["x"] - d["x"]) < 1e-6 or abs(p["y"] - d["y"]) < 1e-6
    for reg in ("A", "B"):
        top = next(i for i, d in n.items() if d.get("rtree_root") == reg)
        leaves = [i for i, d in n.items() if d["taps"] and REG[d["taps"][0][0]] == reg]
        assert all(top in _anc(n, i) for i in leaves)
        assert len(leaves) == sum(1 for t in taps if REG[t[0]] == reg)
        lens = {round(_len(n, i) - _len(n, top), 3) for i in leaves}
        assert len(lens) == 1, (reg, lens)
        for i in leaves:
            for t in n[i]["taps"]:
                assert abs(t[2] - n[i]["x"]) + abs(t[3] - n[i]["y"]) <= 150.0
    # no fishbone nodes
    assert not any(d.get("rib") for d in n.values())
