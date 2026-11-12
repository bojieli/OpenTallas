"""die_clock --pad leg (REACH-FIX-2 11-12, COORD decision B): every H-tree leg of a level is wire-padded to the level's
longest legalised leg; the last mile balances inside its own region; --leaf-pad moves a leaf's own leg only."""
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_clock as DC  # noqa: E402
import schema as S  # noqa: E402

PLAN = HERE / "examples" / "s81_pair" / "s81_pair_plan.json"


def _keep(P):
    T0, _ = DC.build(P, leaf_um=300.0, keep=[], pad="level")
    cells = [c for c in T0.cells.values() if c["kind"] in ("node", "rep")]
    return [(c["x"] - 30.0, c["y"] - 30.0, c["x"] + 30.0, c["y"] + 30.0, f"k{i}") for i, c in enumerate(cells[1::3])]


def _legs(T, tree):
    """node cell -> (level, padded leg length, geometric leg length) from its parent node"""
    into = {}
    for n in T.nets:
        for L, _, load, g in n["branches"]:
            into[load] = (L, g)
    out = {}
    for k, nd in tree["nodes"].items():
        if nd["level"] == 0:
            continue
        par = next(p for p in tree["nodes"].values() if p["level"] == nd["level"] - 1 and p["path"] == nd["path"][:len(p["path"])])
        seg = nd["path"][len(par["path"]):]
        out[k] = (nd["level"], sum(into[c][0] for c in seg), sum(into[c][1] for c in seg))
    return out


def test_leg_pad_equalises_every_level_and_beats_level_pad():
    P = S.Plan(json.loads(PLAN.read_text()))
    keep = _keep(P)
    T, tree = DC.build(P, leaf_um=300.0, keep=keep, pad="leg")
    legs = _legs(T, tree)
    by = defaultdict(set)
    for lev, L, g in legs.values():
        assert L >= g - 1e-6, "a pad never shortens the geometry"
        by[lev].add(round(L, 3))
    assert all(len(v) == 1 for v in by.values()), by
    for n in T.nets:
        for L, _, _, g in n["branches"]:
            assert L >= min(g, 1.0) - 1e-6
    Tl, treel = DC.build(P, leaf_um=300.0, keep=keep, pad="level")
    assert tree["meta"]["padding_um"] < treel["meta"]["padding_um"]
    # last mile: within a region every tap chain has the same padded length
    into = {}
    for n in T.nets:
        for L, _, load, _ in n["branches"]:
            into[load] = L
    reg = defaultdict(set)
    for t in tree["taps"]:
        cut = len(tree["nodes"][t["leaf"]]["path"])
        reg[t["leaf"]].add(round(sum(into[c] for c in t["path"][cut + 1:]) + into["port:" + t["port"]], 3))
    assert all(len(v) == 1 for v in reg.values())


def test_leaf_pad_moves_only_its_own_leg():
    P = S.Plan(json.loads(PLAN.read_text()))
    T0, tree0 = DC.build(P, leaf_um=300.0, keep=[], pad="leg")
    D = tree0["meta"]["levels"]
    leaf = sorted(k for k, n in tree0["nodes"].items() if n["level"] == D)[0]
    T1, tree1 = DC.build(P, leaf_um=300.0, keep=[], pad="leg", leaf_pad={leaf: 120.0})
    a, b = _legs(T0, tree0), _legs(T1, tree1)
    assert abs(b[leaf][1] - a[leaf][1] - 120.0) < 1e-3
    assert all(abs(b[k][1] - a[k][1]) < 1e-6 for k in a if k != leaf)
