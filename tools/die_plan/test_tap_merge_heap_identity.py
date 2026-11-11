"""DIE-QC-97 TAPS-MERGE 11-11: the gridded / indexed _merge is the previous all-pairs heap merge, bit for bit.

The previous form (kept here verbatim as _old_merge / _old_wmedian) offered every leaf pair and sorted the merged sinks
in every offer: QC cand23d su_l0 / su_l1 types never left _merge in a 1800-s strict bind.
    python3 -m pytest -q tools/die_plan/test_tap_merge_heap_identity.py
"""
import heapq
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import taps  # noqa: E402


def _old_wmedian(pts, i):
    s = sorted(pts, key=lambda p: (p[i], p[1 - i]))
    tot, acc = sum(p[2] for p in s), 0.0
    for p in s:
        acc += p[2]
        if acc >= tot / 2:
            return p[i]
    return s[-1][i]


def _old_merge(leaves, target, radius, blocked=lambda x, y: False):
    live = dict(enumerate(leaves))
    pending = []

    def offer(i, j):
        a, b = live[i], live[j]
        if a[2] + b[2] > target or abs(a[0] - b[0]) + abs(a[1] - b[1]) > 2 * radius:
            return
        g = a[4] + b[4]
        x, y = _old_wmedian(g, 0), _old_wmedian(g, 1)
        r = max(abs(p[0] - x) + abs(p[1] - y) for p in g)
        if r <= radius and not blocked(x, y):
            heapq.heappush(pending, (r, i, j, x, y))

    for i in live:
        for j in range(i + 1, len(live)):
            offer(i, j)
    next_id = len(live)
    while pending:
        r, i, j, x, y = heapq.heappop(pending)
        if i not in live or j not in live:
            continue
        a, b = live.pop(i), live.pop(j)
        k = next_id
        next_id += 1
        live[k] = (x, y, a[2] + b[2], r, a[4] + b[4])
        for other in live:
            if other != k:
                offer(other, k)
    return list(live.values())


def _leaves(pts, target, radius, blocked):
    """_bisect's leaves before _merge (same split)."""
    pending, leaves = [pts], []
    while pending:
        g = pending.pop()
        x, y = taps._wmedian(g, 0), taps._wmedian(g, 1)
        n = sum(p[2] for p in g)
        r = max(abs(p[0] - x) + abs(p[1] - y) for p in g)
        if len(g) == 1 or (n <= target and r <= radius and not blocked(x, y)):
            leaves.append((x, y, n, r, g))
            continue
        ax = max((0, 1), key=lambda i: (max(p[i] for p in g) - min(p[i] for p in g), -i))
        g = sorted(g, key=lambda p: (p[ax], p[1 - ax]))
        acc, k = 0.0, 1
        for k, p in enumerate(g[:-1], 1):
            acc += p[2]
            if acc >= n / 2:
                break
        pending += [g[k:], g[:k]]
    return leaves


CORES = ((190.08, 34.56, 604.8, 302.4), (190.08, 354.24, 604.8, 622.08), (190.08, 725.76, 604.8, 993.6))


_blocked = taps._Keepout(CORES)


def _blocked_plain(x, y):
    return any(x0 < x < x1 and y0 < y < y1 for x0, y0, x1, y1 in CORES)


def _su_like(seed, n):
    """per-bit station / face sinks around hard cores: unit and bin weights, lattice duplicates, a few odd values."""
    R = random.Random(seed)
    pts = []
    for k in range(n):
        if k % 3 == 0:          # dense face bands at the core edges (duplicate x, many equal keys)
            x0, y0, x1, y1 = CORES[R.randrange(3)]
            x = R.choice((x0 - 4.32, x1 + 4.32))
            y = round(R.uniform(y0, y1) / 0.54) * 0.54 + 0.27
        else:
            x, y = R.uniform(2.0, 620.0), R.uniform(2.0, 1337.0)
        pts.append((x, y, float(R.choice((1, 1, 1, 2, 7)))))
    return pts


def _same(a, b):
    return repr(a) == repr(b)


def test_identity_mixed_weights_and_fallbacks():
    R = random.Random(97)
    for seed in range(40):
        n = R.choice((60, 250, 700))
        pts = _su_like(seed, n)
        if seed % 4 == 1:       # fractional weights: _wmedian fallback
            pts = [(x, y, w / 4) for x, y, w in pts]
        if seed % 4 == 2:       # integer / zero coordinates: _wmedian and full-radius fallbacks for those leaves
            pts = [(0.0 if k % 17 == 0 else int(x) if k % 13 == 0 else x, y, w) for k, (x, y, w) in enumerate(pts)]
        target, radius = R.choice((8, 40, 200)), R.choice((30.0, 80.0, 200.0))
        blocked = (_blocked, _blocked_plain, (lambda x, y: False))[seed % 3]
        leaves = _leaves(pts, target, radius, blocked)
        assert _same(taps._merge(leaves, target, radius, blocked), _old_merge(leaves, target, radius, blocked)), seed


def test_identity_and_speed_5k_leaves():
    pts = _su_like(1111, 13000)
    target, radius = 24, 60.0
    leaves = _leaves(pts, target, radius, _blocked)
    assert len(leaves) >= 4500
    t0 = time.perf_counter()
    old = _old_merge(leaves, target, radius, _blocked)
    t1 = time.perf_counter()
    new = taps._merge(leaves, target, radius, _blocked)
    t2 = time.perf_counter()
    assert _same(new, old)
    assert t2 - t1 < (t1 - t0) / 2, (t1 - t0, t2 - t1)      # measured 11.5 s -> 2.9 s at 4.5k leaves (epyc7)
