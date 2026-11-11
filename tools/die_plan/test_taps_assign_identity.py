"""TAPS-ASSIGN (DIE-QC-97 11-11): taps.assign must give the reference result bit for bit.

The reference below is a verbatim copy of taps.assign before the numpy form (main 11-11).  Every case compares the
full return value (loads, far distances, assignment) with repr(), so float bits and int / float types both count."""
import os
import random
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taps  # noqa: E402


def assign_ref(taps, sinks, cap, max_extra_um, max_distance_um=None):
    xy = [(t[1], t[2]) for t in taps]
    d = lambda s, j: abs(s[0] - xy[j][0]) + abs(s[1] - xy[j][1])
    asg = [min(range(len(xy)), key=lambda j: (d(s, j), j)) for s in sinks]
    load = [0.0] * len(xy)
    for s, j in zip(sinks, asg):
        load[j] += s[2]
    stuck = set()
    for _ in range(8 * len(xy)):
        over = next((j for j in range(len(xy)) if j not in stuck and load[j] > cap), None)
        if over is None:
            break
        cand = []
        for i, s in enumerate(sinks):
            if asg[i] != over:
                continue
            best = min(((d(s, j) - d(s, over), j) for j in range(len(xy))
                        if j != over and load[j] < cap
                        and (max_distance_um is None or d(s, j) <= max_distance_um)),
                       default=None)
            if best and best[0] <= max_extra_um:
                cand.append((best[0], i, best[1]))
        if not cand:
            stuck.add(over)
            continue
        cand.sort()
        tgt = cand[0][2]
        for _, i, j in cand:
            if load[over] <= cap or load[tgt] >= cap:
                break
            if j != tgt:
                continue
            asg[i] = tgt
            load[over] -= sinks[i][2]
            load[tgt] += sinks[i][2]
    far = [0.0] * len(xy)
    for s, j in zip(sinks, asg):
        far[j] = max(far[j], d(s, j))
    return load, far, asg


def _same(tc, a, b):
    tc.assertEqual(repr(a), repr(b))


def _run(fn, *a, **k):
    try:
        return ("ok", fn(*a, **k))
    except Exception as e:  # the same failure (type + message) is part of the identity
        return ("err", type(e).__name__, str(e))


class AssignIdentity(unittest.TestCase):
    def check(self, tp, sk, cap, extra, maxd):
        _same(self, _run(taps.assign, tp, sk, cap, extra, max_distance_um=maxd),
              _run(assign_ref, tp, sk, cap, extra, max_distance_um=maxd))

    def test_randomized(self):
        rng = random.Random(1111)
        for case in range(300):
            nt, ns = rng.randint(1, 40), rng.randint(1, 400)
            grid = rng.choice([None, 2.16, 1.0, 0.5])
            span = rng.choice([50.0, 300.0, 2000.0])
            q = (lambda v: v) if grid is None else (lambda v: round(round(v / grid) * grid, 4))
            tp = [(None, q(rng.uniform(0, span)), q(rng.uniform(0, span))) for _ in range(nt)]
            if nt > 2 and rng.random() < 0.3:
                tp[rng.randrange(nt)] = tp[0]            # duplicate tap: every sink ties on it
            sk = [(q(rng.uniform(0, span)), q(rng.uniform(0, span)), rng.choice([1, 1.0, 0.5, 2, 3.0]))
                  for _ in range(ns)]
            cap = rng.choice([1, 3, 10, max(1, ns // nt), ns])
            extra = rng.choice([0.0, 5.0, span / 4, 1e9])
            maxd = rng.choice([None, span / 8, span / 3, 1e9])
            self.check(tp, sk, cap, extra, maxd)
            # the vector form itself ran (not the reference fallback)
            self.assertIsNotNone(taps._assign_np([(t[1], t[2]) for t in tp], sk, cap, extra, maxd))

    def test_ties(self):
        # a symmetric lattice: every sink equidistant from 2 or 4 taps, re-assignment deltas tie too
        tp = [(None, x, y) for y in (0.0, 10.0) for x in (0.0, 10.0)]
        sk = [(5.0, 5.0, 1.0)] * 9 + [(5.0, 0.0, 1.0)] * 5 + [(0.0, 5.0, 1)] * 5
        for cap in (1, 2, 4, 5, 19):
            for extra in (0.0, 5.0, 100.0):
                for maxd in (None, 5.0, 10.0, 7.5):
                    self.check(tp, sk, cap, extra, maxd)

    def test_ints_and_mixed(self):
        rng = random.Random(7)
        tp = [(None, rng.randint(0, 50), rng.randint(0, 50)) for _ in range(12)]
        sk = [(rng.randint(0, 50), float(rng.randint(0, 50)), rng.choice([1, 2])) for _ in range(300)]
        for cap in (5, 20, 40):
            self.check(tp, sk, cap, 10, 30)
            self.check(tp, sk, cap, 10.0, None)

    def test_blocked_and_stuck(self):
        # every other tap out of reach (max distance) or full: the over tap goes stuck, nothing moves
        tp = [(None, 0.0, 0.0), (None, 1000.0, 1000.0), (None, 0.0, 1.0)]
        sk = [(0.1 * i, 0.0, 1.0) for i in range(50)]
        for cap in (1, 10, 25, 49, 50):
            for maxd in (None, 0.5, 2.0, 5.0):
                self.check(tp, sk, cap, 3.0, maxd)
                self.check(tp, sk, cap, -1.0, maxd)

    def test_empty_and_single(self):
        self.check([], [], 1, 1.0, None)
        self.check([], [(0.0, 0.0, 1.0)], 1, 1.0, None)          # the reference raises; so must assign
        self.check([(None, 1.0, 2.0)], [], 1, 1.0, None)
        self.check([(None, 1.0, 2.0)], [(0.0, 0.0, 1.0)] * 3, 1, 1.0, 5.0)

    def test_non_plain_inputs_fall_back(self):
        nan, inf = float("nan"), float("inf")
        tp = [(None, 0.0, 0.0), (None, inf, 1.0), (None, 2.0, nan)]
        sk = [(0.5, 0.5, 1.0), (nan, 1.0, 1.0), (3.0, 3.0, 1.0)] * 4
        self.check(tp, sk, 2, 10.0, None)
        big = 1 << 60
        self.check([(None, big, 0), (None, -big, 0)], [(big - 1, 0, 1), (-big + 3, 0, 1), (0, 0, 1)], 1, 1 << 62, None)

    def test_speed(self):
        # a QC su-like case (dense sinks, a few hundred taps): the reference needs minutes here
        rng = random.Random(3)
        sk = [(round(rng.uniform(0, 2000), 4), round(rng.uniform(0, 2000), 4), 1.0) for _ in range(30000)]
        tp = [(None, round(rng.uniform(0, 2000), 4), round(rng.uniform(0, 2000), 4)) for _ in range(300)]
        t0 = time.perf_counter()
        a = taps.assign(tp, sk, 80, 200.0, max_distance_um=200.0)
        dt = time.perf_counter() - t0
        self.assertLess(dt, 30.0)
        # identity on a slice the reference can afford
        _same(self, taps.assign(tp[:60], sk[:3000], 40, 200.0, max_distance_um=200.0),
              assign_ref(tp[:60], sk[:3000], 40, 200.0, max_distance_um=200.0))
        self.assertEqual(len(a[2]), len(sk))


# Verbatim copy of schema.tap_clear before the nearest-column search (main 11-11); module names bound from schema.
import math  # noqa: E402
import schema  # noqa: E402
import gen_phys  # noqa: E402
TAP_CLEAR_UM, TAP_STEP_UM, placed_macro_boxes = schema.TAP_CLEAR_UM, schema.TAP_STEP_UM, schema.placed_macro_boxes


def tap_clear_ref(t, x, y, taken=(), clear=TAP_CLEAR_UM, strict=False, *, pin_snap=None, legal_axes=None):
    """S81-P8 10-23 (GEOM-REVIEW5 15:14 condition (b)): an R4 grid tap at a cell centre landed ON a ROM / hard-core
    macro in 4-10 of 10 interior pins of the S81 frame kits (h9_r1: all), so its root buffer sat on a macro.  Move the
    tap to the nearest point (rings of 2.16 um) that is >= `clear` from every hard_cores box of the type (a channel),
    inside the outline by `clear`, and >= `clear` from the taps already placed.  Types without hard cores, or whose
    tap is already in a channel, are unchanged (strict=True, density taps: the outline / taken spacing applies even
    without hard cores)."""
    w, h = t["outline_um"]
    # Density clock pins are consumed on PG-safe routing tracks. Their legal
    # candidate axes come from gen_phys, rather than an anchor lattice that
    # can disappear when the pin is snapped. Other callers retain the legacy
    # anchor search. Keep both early-core anchors and consumed pins reserved.
    if (pin_snap is None) != (legal_axes is None):
        raise ValueError('consumed clock placement requires both pin_snap and legal_axes')
    eps = 1e-8 if legal_axes is not None else 0.0
    if pin_snap is not None:
        taken = list(taken) + [pin_snap(a, b) for a, b in taken]
    keep = [(a - clear, b - clear, c + clear, d + clear) for a, b, c, d in t.get("clock", {}).get("keepouts_um", [])]
    # a macro wholly inside a clock keepout blocks nothing the keepout does not (S81 PMA in the shore keepout): its box
    # would only add candidate edges and move grid taps that tie on the ring distance
    from placement_obstacles import placement_boxes
    if t.get("clock", {}).get("tap_model") == "frozen_anchor":
        pool = placed_macro_boxes(t, halo=clear)
    else:
        pool = placement_boxes(t, halo=clear)
    boxes = [m for m in pool.values()
             if not any(k[0] <= m[0] and k[1] <= m[1] and m[2] <= k[2] and m[3] <= k[3] for k in keep)] + keep

    def free(px, py):
        if not (clear - eps <= px <= w - clear + eps and clear - eps <= py <= h - clear + eps):
            return False
        if any(abs(px - a) < clear - eps and abs(py - b) < clear - eps for a, b in taken):
            return False
        return not any(x0 + eps < px < x1 - eps and y0 + eps < py < y1 - eps
                       for x0, y0, x1, y1 in boxes)
    consumed = pin_snap(x, y) if pin_snap is not None else (x, y)
    if (not boxes and not strict) or free(*consumed):
        return consumed
    # Legal regions have axis-aligned boundaries. Project each boundary onto the same origin-centred 2.16-um
    # lattice as the old expanding rings; their Cartesian product contains the nearest legal ring site. This
    # avoids enumerating millions of interior points when an analog window pushes a tap hundreds of um.
    def candidates(origin, extent, edges, axis):
        if legal_axes is not None:
            from bisect import bisect_left
            tracks = legal_axes[axis]
            values = set()
            for edge in [origin, clear, extent - clear] + list(edges):
                j = bisect_left(tracks, edge)
                values.update(tracks[k] for k in (j - 1, j) if 0 <= k < len(tracks))
            return values
        values = {origin}
        for edge in [clear, extent - clear] + list(edges):
            q = (edge - origin) / TAP_STEP_UM
            for k in (math.floor(q), math.ceil(q)):
                v = round(origin + k * TAP_STEP_UM, 8)
                if clear - 1e-7 <= v <= extent - clear + 1e-7:
                    values.add(v)
        return values
    obs = boxes + [(a - clear, b - clear, a + clear, b + clear) for a, b in taken]
    xs = candidates(x, w, [v for a, b, c, d in obs for v in (a, c)], 0)
    ys = candidates(y, h, [v for a, b, c, d in obs for v in (b, d)], 1)
    # Each obstacle blocks the same Y candidates for every X column. Compute
    # those exact comparisons once, then combine bitmasks per column instead
    # of scanning every obstacle at every Cartesian candidate. Keep abs() for
    # taken taps: rewriting it as interval bounds changes floating edge cases.
    ys = list(ys)
    inside = sum(1 << i for i, py in enumerate(ys) if clear - eps <= py <= h - clear + eps)
    blockers = [(x0, x1, sum(1 << i for i, py in enumerate(ys) if y0 + eps < py < y1 - eps))
                for x0, y0, x1, y1 in boxes]
    neighbours = [(a, sum(1 << i for i, py in enumerate(ys) if abs(py - b) < clear - eps))
                  for a, b in taken]
    def legal_candidates():
        for px in xs:
            if not clear - eps <= px <= w - clear + eps:
                continue
            bits = inside
            for x0, x1, blocked in blockers:
                if x0 + eps < px < x1 - eps:
                    bits &= ~blocked
            for a, blocked in neighbours:
                if abs(px - a) < clear - eps:
                    bits &= ~blocked
            while bits:
                low = bits & -bits
                yield px, ys[low.bit_length() - 1]
                bits ^= low
    ok = legal_candidates()
    best = min(ok, key=lambda p: (round(abs(p[0] - x) + abs(p[1] - y) if legal_axes is not None
                                      else max(abs(p[0] - x), abs(p[1] - y)), 7),
                                  (p[0] - x) ** 2 + (p[1] - y) ** 2, p), default=None)
    if best is not None:
        return round(best[0], 4), round(best[1], 4)
    raise ValueError(f"no legal clock tap site in {t.get('module', 'type')} near ({x}, {y}); "
                     f"clearance {clear} um, {len(boxes)} keepouts")


class _Plan:
    layer_budget = {'partition_signal_max': 'M7'}
    layers = {'M7': {'dir': 'V', 'pitch_um': .08, 'offset_um': .04},
              'M6': {'dir': 'H', 'pitch_um': .064, 'offset_um': .032}}

    def __init__(self, t):
        self.types = {'t': t}


def _rand_type(rng, hard=False):
    w = round(rng.choice([60.0, 120.0, 300.0]) / 2.16) * 2.16
    h = round(rng.choice([60.0, 120.0, 300.0]) / 2.16) * 2.16
    cores = []
    for k in range(rng.randint(0, 6)):
        cw, ch = rng.uniform(5, w / 2), rng.uniform(5, h / 2)
        cores.append({'inst': f'c{k}', 'origin_um': [rng.uniform(0, w - cw), rng.uniform(0, h - ch)],
                      'outline_um': [cw, ch]})
    t = {'module': 'fx', 'outline_um': [w, h], 'hard_cores': cores, 'hard': hard}
    if rng.random() < 0.3:
        x0, y0 = rng.uniform(0, w / 2), rng.uniform(0, h / 2)
        t['clock'] = {'keepouts_um': [[x0, y0, x0 + rng.uniform(5, w / 3), y0 + rng.uniform(5, h / 3)]]}
    return t


class TapClearIdentity(unittest.TestCase):
    def both(self, *a, **k):
        _same(self, _run(schema.tap_clear, *a, **k), _run(tap_clear_ref, *a, **k))

    def test_randomized_lattice_and_consumed(self):
        rng = random.Random(1111)
        for case in range(400):
            t = _rand_type(rng, hard=rng.random() < 0.2)
            w, h = t['outline_um']
            taken = [(round(rng.uniform(0, w), 4), round(rng.uniform(0, h), 4)) for _ in range(rng.randint(0, 25))]
            if taken and rng.random() < 0.3:
                taken.append(taken[0])                       # a duplicate taken tap
            x, y = rng.uniform(-5, w + 5), rng.uniform(-5, h + 5)
            if rng.random() < 0.3 and taken:
                x, y = taken[-1]                             # exactly on a taken tap: symmetric ring ties
            strict = rng.random() < 0.7
            self.both(t, x, y, taken, strict=strict)
            P = _Plan(t)
            snap = lambda a, b: gen_phys._snap_tap(P, a, b, pg_legal=not t.get('hard'))
            axes = gen_phys.clock_legal_axes(P, 't')
            self.both(t, x, y, taken, strict=True, pin_snap=snap, legal_axes=axes)
            self.both(t, x, y, taken, strict=True, pin_snap=taps._memo_snap(snap), legal_axes=axes)

    def test_ties_on_symmetric_box(self):
        # a centred square macro: the tap at its centre is equidistant from all four channels
        t = {'module': 'fx', 'outline_um': [86.4, 86.4],
             'hard_cores': [{'inst': 'm', 'origin_um': [21.6, 21.6], 'outline_um': [43.2, 43.2]}]}
        P = _Plan(t)
        snap = lambda a, b: gen_phys._snap_tap(P, a, b)
        axes = gen_phys.clock_legal_axes(P, 't')
        for taken in ([], [(43.2, 8.64)], [(8.64, 43.2), (77.76, 43.2)]):
            self.both(t, 43.2, 43.2, taken, strict=True)
            self.both(t, 43.2, 43.2, taken, strict=True, pin_snap=snap, legal_axes=axes)

    def test_no_legal_site_and_non_finite(self):
        t = {'module': 'fx', 'outline_um': [20.0, 20.0],
             'hard_cores': [{'inst': 'm', 'origin_um': [0.0, 0.0], 'outline_um': [20.0, 20.0]}]}
        self.both(t, 10.0, 10.0, [], strict=True)              # both raise the same ValueError
        t2 = _rand_type(random.Random(5))
        self.both(t2, float('nan'), 10.0, [], strict=True)
        self.both(t2, float('inf'), 10.0, [(1.0, 1.0)], strict=True)

    def test_speed(self):
        rng = random.Random(9)
        t = _rand_type(rng)
        t['hard_cores'] = [{'inst': f'c{k}', 'origin_um': [20.0 + 30 * (k % 30), 20.0 + 30 * (k // 30)],
                            'outline_um': [12.0, 12.0]} for k in range(300)]
        t['outline_um'] = [940.0, 340.0]
        taken = [(20.0 + 30 * (k % 30) + 6, 20.0 + 30 * (k // 30) + 6) for k in range(300)]
        t0 = time.perf_counter()
        for k in range(20):
            q = schema.tap_clear(t, taken[k][0], taken[k][1], taken, strict=True)
        dt = time.perf_counter() - t0
        self.assertLess(dt, 20.0)
        _same(self, q, tap_clear_ref(t, taken[19][0], taken[19][1], taken, strict=True))


if __name__ == "__main__":
    unittest.main()
