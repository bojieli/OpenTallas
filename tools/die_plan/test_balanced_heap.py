"""Exact correction-order checks for balanced clustering's heap implementation."""
import collections
import random
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import core_infra_htree as H

def legacy_balanced(points, centres, dist, iters=400):
    n = len(points); k = len(centres); tgt = [n // k + (1 if i < n % k else 0) for i in range(k)]
    Dm = [[dist(p, c) for c in centres] for p in points]; w = [0.0] * k
    for it in range(iters):
        a = [min(range(k), key=lambda c: Dm[i][c] + w[c]) for i in range(n)]; cnt = collections.Counter(a)
        if all(cnt[c] == tgt[c] for c in range(k)): break
        for c in range(k): w[c] += 0.5 * (cnt[c] - tgt[c]) / max(1, n / k) * 20 / (1 + it / 50)
    cnt = collections.Counter(a)
    while any(cnt[c] > tgt[c] for c in range(k)):
        best = None
        for i in range(n):
            if cnt[a[i]] <= tgt[a[i]]: continue
            for c in range(k):
                if cnt[c] < tgt[c]:
                    cost = Dm[i][c] - Dm[i][a[i]]
                    if best is None or cost < best[0]: best = (cost, i, c)
        _, i, c = best; cnt[a[i]] -= 1; cnt[c] += 1; a[i] = c
    return [[points[i] for i in range(n) if a[i] == c] for c in range(k)]



def test_heap_matches_legacy_assignments_and_ties():
    for seed in range(24):
        rng = random.Random(seed)
        n = 37 + seed * 3; k = 2 + seed % 6
        points = [(rng.randrange(12) / (3 if seed % 2 else 1), rng.randrange(12) / (3 if seed % 2 else 1), i) for i in range(n)]
        centres = [(rng.randrange(12), rng.randrange(12)) for _ in range(k)]
        dist = lambda p, c: abs(p[0] - c[0]) + abs(p[1] - c[1])
        assert H.balanced(points, centres, dist, iters=1 + seed % 4) == legacy_balanced(points, centres, dist, iters=1 + seed % 4)
    points = list(range(31)); centres = list(range(7))
    assert H.balanced(points, centres, lambda p, c: 0, iters=1) == legacy_balanced(points, centres, lambda p, c: 0, iters=1)


def test_heap_preserves_all_points_and_exact_target_loads():
    points = list(range(101)); centres = list(range(8))
    result = H.balanced(points, centres, lambda p, c: abs(p - 10*c), iters=1)
    assert sorted(p for group in result for p in group) == points
    assert [len(g) for g in result] == [13]*5 + [12]*3


def test_optional_numpy_fallback_preserves_legacy_order(monkeypatch):
    import builtins
    original = builtins.__import__
    def without_numpy(name, *args, **kwargs):
        if name == "numpy":
            raise ImportError("minimal environment")
        return original(name, *args, **kwargs)
    points = [(i / 3, i % 7) for i in range(55)]; centres = [(0, 1), (6, 3), (16, 2)]
    distance = lambda p, c: abs(p[0] - c[0]) + abs(p[1] - c[1])
    expected = H.balanced(points, centres, distance, iters=13)
    monkeypatch.setattr(builtins, "__import__", without_numpy)
    assert H.balanced(points, centres, distance, iters=13) == expected == legacy_balanced(points, centres, distance, iters=13)


def test_nonfinite_distances_keep_legacy_scalar_correction_order():
    points = list(range(11)); centres = list(range(3))
    for special in (float("nan"), float("inf"), -float("inf")):
        distance = lambda p, c: special if p == 0 and c == 1 else float(abs(p - c))
        assert H.balanced(points, centres, distance, iters=2) == legacy_balanced(points, centres, distance, iters=2)
