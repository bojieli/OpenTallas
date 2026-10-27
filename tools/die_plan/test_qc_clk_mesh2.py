import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import qc_clk_mesh2 as M


def _paths(nodes, by):
    out = []
    for n in nodes:
        if n["kids"]:
            continue
        L = S = 0
        t = n
        while t.get("parent"):
            p = by[t["parent"]]
            L += M.md(p["xy"], t["xy"])
            S += t["nseg"]
            t = p
        out.append((round(L, 6), S))
    return out


def test_gtree_non_pow2_equal_length_and_stages():
    cols = [100 + 622.08 * i for i in range(49)]
    rows = [200 + 410 * j for j in range(7)]
    nodes, by = M.gtree(cols, rows, None)
    p = _paths(nodes, by)
    assert len(p) == 49 * 7
    assert len({x[0] for x in p}) == 1 and len({x[1] for x in p}) == 1


def test_gtree_gap_equal_and_no_detour():
    cols = [100 + 622.08 * i for i in range(49)]
    gaps = [1300 * k + 650 for k in range(16)]
    nodes, by = M.gtree_gap(cols, gaps, 432.0, 21000.0)
    p = _paths(nodes, by)
    assert len({x[0] for x in p}) == 1 and len({x[1] for x in p}) == 1
    # no detour: every leg is the straight Manhattan distance and each node lies between its children
    for n in nodes:
        if n["kids"]:
            a, b = (by[k] for k in n["kids"])
            ax = 0 if n["ax"] == "x" else 1
            lo, hi = sorted((a["xy"][ax], b["xy"][ax]))
            assert lo - 1e-6 <= n["xy"][ax] <= hi + 1e-6
    # x-trees run ON the gap rows
    for n in nodes:
        if n["ax"] == "x":
            assert min(abs(n["xy"][1] - g) for g in gaps) < 1.0
