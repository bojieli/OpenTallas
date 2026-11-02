"""Incremental merge must retain the original deterministic geometry and leaf order."""
import random
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import taps
from taps import _wmedian

def reference_merge(leaves, target, radius, blocked=lambda x, y: False):
    """bisection cuts along the median, so a sparse channel or an L-shaped region ends up in many small leaves (dead-ish
    taps of a few hundred sinks next to each other).  Greedily merge the pair of leaves whose union still fits the
    target and radius with the smallest merged radius, until no pair fits.  Deterministic."""
    leaves = list(leaves)
    while True:
        best = None
        for i, a in enumerate(leaves):
            for j in range(i + 1, len(leaves)):
                b = leaves[j]
                if a[2] + b[2] > target or abs(a[0] - b[0]) + abs(a[1] - b[1]) > 2 * radius:
                    continue
                g = a[4] + b[4]
                x, y = _wmedian(g, 0), _wmedian(g, 1)
                r = max(abs(p[0] - x) + abs(p[1] - y) for p in g)
                if r <= radius and not blocked(x, y) and (best is None or (r, i, j) < best[:3]):
                    best = (r, i, j, (x, y, a[2] + b[2], r, g))
        if best is None:
            return leaves
        _, i, j, m = best
        leaves = [q for k, q in enumerate(leaves) if k not in (i, j)] + [m]


def leaf(x,y,n=1):
    return (x,y,n,0,[(x,y,n)])

def test_equal_radius_ties_and_new_leaf_order():
    points=[leaf(0,0) for _ in range(7)]
    assert taps._merge(points,3,10)==reference_merge(points,3,10)
    # Point order is observable in later stable weighted-median sorts.
    points=[leaf(i%3,i//3) for i in range(18)]
    assert taps._merge(points,4,4)==reference_merge(points,4,4)

def test_capacity_radius_and_macro_keepouts_match_reference():
    rng=random.Random(6001)
    for _ in range(80):
        points=[leaf(rng.randrange(30),rng.randrange(30),rng.randrange(1,5)) for _ in range(rng.randrange(1,35))]
        target=rng.randrange(3,15);radius=rng.randrange(2,20)
        blocked=lambda x,y: 8<x<17 and 9<y<19
        assert taps._merge(points,target,radius,blocked)==reference_merge(points,target,radius,blocked)

def test_unchanged_pair_costs_are_reused(monkeypatch):
    points=[leaf(i%8,i//8) for i in range(64)]
    original=taps._wmedian;calls=[]
    def count(*args):
        calls.append(1)
        return original(*args)
    monkeypatch.setattr(taps,'_wmedian',count)
    want=reference_merge(points,16,100)
    # Reference uses this module's original median; count it separately.
    reference_calls=[]
    def count_ref(*args):
        reference_calls.append(1)
        return original(*args)
    monkeypatch.setitem(reference_merge.__globals__,'_wmedian',count_ref)
    assert reference_merge(points,16,100)==want
    got=taps._merge(points,16,100)
    assert got==want and len(calls)<len(reference_calls)/4
