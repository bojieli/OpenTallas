"""opentools.mscts street-aware routing (OSS-CLOCK-3): clock wires follow the legal STREETS between keepouts so every
repeater stage can sit on a legal site, and merge buffers sit on a legal point of their zero-skew MERGING SEGMENT
instead of being pushed along one fixed L path and re-balanced by meander.

Generic: the only inputs are the keepout rects (mscts.legal.Legality, from the plan schema) and the repeater reach.
  * a wire may cross a keepout (top metal over a hard core); only BUFFERS must be legal.  The cost of a route is
    therefore its longest arc interval inside keepouts (no repeater possible there), then its bend count.
  * candidate routes a -> b are MONOTONE staircases (length = Manhattan distance, so zero extra wire): the two L
    paths, Z paths through a street column / row (keepout edge +- 1 um), and 3-bend column+row paths.  Street lines
    are derived from the keepout edges, no die-specific data.
  * merging segment (DME): for a split x of the Manhattan distance D, every point p with |p - a| = x, |p - b| = D - x
    inside the bounding box balances the pair equally well; the merge buffer takes the LEGAL point of that segment
    whose two routes have the shortest unrepeatable span.
  * repeaters: equal spacing over the remaining length, an ideal position inside a keepout snaps to the keepout edge
    (back if the stage stays <= reach, else forward); stages are exact lengths, delays use them (no post-hoc skew).
"""
import math

EPS = 0.05


def plen(pts):
    return sum(abs(q[0] - p[0]) + abs(q[1] - p[1]) for p, q in zip(pts, pts[1:]))


def at(pts, s):
    """point at arc length s along the polyline (clamped to its end)."""
    for p, q in zip(pts, pts[1:]):
        L = abs(q[0] - p[0]) + abs(q[1] - p[1])
        if s <= L + 1e-9:
            if L <= 0:
                return tuple(p)
            f = s / L
            return (p[0] + f * (q[0] - p[0]), p[1] + f * (q[1] - p[1]))
        s -= L
    return tuple(pts[-1])


def sub(pts, s0, s1):
    """sub-polyline between arc s0 and s1 (clamped)."""
    out = [at(pts, s0)]
    acc = 0.0
    for p, q in zip(pts, pts[1:]):
        L = abs(q[0] - p[0]) + abs(q[1] - p[1])
        acc += L
        if s0 < acc < s1:
            out.append(tuple(q))
    out.append(at(pts, s1))
    return out


def _clean(pts):
    out = [tuple(pts[0])]
    for p in pts[1:]:
        p = tuple(p)
        if abs(p[0] - out[-1][0]) + abs(p[1] - out[-1][1]) < 1e-9:
            continue
        if len(out) >= 2:
            o, q = out[-2], out[-1]
            if (abs(o[0] - q[0]) < 1e-9 and abs(q[0] - p[0]) < 1e-9) or (abs(o[1] - q[1]) < 1e-9 and abs(q[1] - p[1]) < 1e-9):
                out[-1] = p
                continue
        out.append(p)
    if len(out) == 1:
        out.append(out[0])
    return out


class Router:
    def __init__(self, legal, rep_um, ncand=3, jog=False):
        self.L = legal
        self.jog = jog      # off-box jog routes: measured worse on QC E0 (snake 4.99% -> 16%), kept opt-in
        self.rep = float(rep_um)
        self.ncand = ncand
        k = legal.k
        self.xs = sorted({round(r[0] - 1.0, 3) for r in k} | {round(r[2] + 1.0, 3) for r in k})
        self.ys = sorted({round(r[1] - 1.0, 3) for r in k} | {round(r[3] + 1.0, 3) for r in k})
        self.cache = {}

    def kos(self, a, b, pad=1.0):
        x0, x1 = min(a[0], b[0]) - pad, max(a[0], b[0]) + pad
        y0, y1 = min(a[1], b[1]) - pad, max(a[1], b[1]) + pad
        return [r for r in self.L.k if r[0] < x1 and r[2] > x0 and r[1] < y1 and r[3] > y0]

    @staticmethod
    def blocked(pts, kos):
        """merged arc intervals of the polyline strictly inside a keepout (no buffer site)."""
        out = []
        s0 = 0.0
        for p, q in zip(pts, pts[1:]):
            L = abs(q[0] - p[0]) + abs(q[1] - p[1])
            if L > 0:
                hz = abs(q[1] - p[1]) < 1e-9
                for r in kos:
                    if hz:
                        if r[1] < p[1] < r[3]:
                            lo, hi = max(min(p[0], q[0]), r[0]), min(max(p[0], q[0]), r[2])
                            if hi > lo:
                                a_, b_ = abs(lo - p[0]), abs(hi - p[0])
                                out.append((s0 + min(a_, b_), s0 + max(a_, b_)))
                    else:
                        if r[0] < p[0] < r[2]:
                            lo, hi = max(min(p[1], q[1]), r[1]), min(max(p[1], q[1]), r[3])
                            if hi > lo:
                                a_, b_ = abs(lo - p[1]), abs(hi - p[1])
                                out.append((s0 + min(a_, b_), s0 + max(a_, b_)))
            s0 += L
        out.sort()
        m = []
        for a, b in out:
            if m and a <= m[-1][1] + 1e-9:
                m[-1][1] = max(m[-1][1], b)
            else:
                m.append([a, b])
        return m

    def score(self, pts, kos):
        iv = self.blocked(pts, kos)
        mb = max((b - a for a, b in iv), default=0.0)
        return (round(max(0.0, mb - (self.rep - 2 * EPS)), 3), len(pts) - 2, round(mb, 3)), iv

    def _near(self, vals, lo, hi, refs):
        c = [v for v in vals if lo < v < hi]
        best = set()
        for r in refs:
            best.update(sorted(c, key=lambda v: abs(v - r))[:self.ncand])
        return sorted(best)

    def route(self, a, b):
        """-> (polyline a .. b, blocked intervals, score); monotone (length = Manhattan distance)."""
        a, b = (float(a[0]), float(a[1])), (float(b[0]), float(b[1]))
        key = (round(a[0], 3), round(a[1], 3), round(b[0], 3), round(b[1], 3))
        if key in self.cache:
            return self.cache[key]
        kos = self.kos(a, b)
        cands = [[a, (b[0], a[1]), b], [a, (a[0], b[1]), b]]
        if kos:
            xc = self._near(self.xs, min(a[0], b[0]), max(a[0], b[0]), (a[0], b[0]))
            yr = self._near(self.ys, min(a[1], b[1]), max(a[1], b[1]), (a[1], b[1]))
            cands += [[a, (x, a[1]), (x, b[1]), b] for x in xc]
            cands += [[a, (a[0], y), (b[0], y), b] for y in yr]
            cands += [[a, (a[0], y), (x, y), (x, b[1]), b] for x in xc for y in yr]
            cands += [[a, (x, a[1]), (x, y), (b[0], y), b] for x in xc for y in yr]
        best = None
        for c in cands:
            c = _clean(c)
            sc, iv = self.score(c, kos) if kos else (((0.0, len(_clean(c)) - 2, 0.0)), [])
            sc = (sc[0], 0.0) + tuple(sc[1:])
            if best is None or sc < best[2]:
                best = (c, iv, sc)
            if sc[0] == 0 and sc[3] == 0 and sc[2] == 0:
                break
        if self.jog and best[2][0] > 0:
            # no monotone street route keeps every unrepeatable span <= reach: JOG out of the bounding box into the
            # nearest street column / row (extra wire 2 x jog, reported as route length > Manhattan)
            x0b, x1b, y0b, y1b = min(a[0], b[0]), max(a[0], b[0]), min(a[1], b[1]), max(a[1], b[1])
            xo = sorted((v for v in self.xs if v < x0b or v > x1b), key=lambda v: max(x0b - v, v - x1b))[:2 * self.ncand]
            yo = sorted((v for v in self.ys if v < y0b or v > y1b), key=lambda v: max(y0b - v, v - y1b))[:2 * self.ncand]
            jog = [[a, (x, a[1]), (x, b[1]), b] for x in xo] + [[a, (a[0], y), (b[0], y), b] for y in yo]
            for c in jog:
                c = _clean(c)
                k2 = self.kos(*(((min(p[0] for p in c), min(p[1] for p in c)), (max(p[0] for p in c), max(p[1] for p in c)))))
                sc, iv = self.score(c, k2)
                sc = (sc[0], round(plen(c) - (abs(b[0] - a[0]) + abs(b[1] - a[1])), 3)) + tuple(sc[1:])
                if sc < best[2]:
                    best = (c, iv, sc)
        best = (best[0], best[1], (best[2][0],) + tuple(best[2][2:]))   # (over, bends, max span) as before
        self.cache[key] = best
        return best


def _snap(D, L, iv, rep, n):
    """n stages: ideal equal positions, each one inside a keepout snapped to the nearer edge whose adjacent stages
    stay <= rep (else the other edge); -> positions or None if a stage still exceeds rep."""
    pos = []
    for r in range(1, n):
        s = L * r / n
        v = next((v for v in iv if v[0] < s < v[1]), None) if s < D else None
        if v is not None:
            back, fwd = v[0] - EPS, v[1] + EPS
            prev = pos[-1] if pos else 0.0
            nxt = L * (r + 1) / n
            opts = [x for x in (back, fwd) if prev + 1e-6 < x < L - 1e-6]
            if not opts:
                return None
            ok = [x for x in opts if x - prev <= rep + 1e-9 and nxt - x <= rep + 1e-9]
            s = min(ok or opts, key=lambda x: abs(x - s))
        if pos and s <= pos[-1] + 1e-6:
            return None
        pos.append(s)
    return pos


def place(D, L, iv, rep):
    """stage lengths for a wire of total length L >= D whose first D um follow a route with blocked intervals iv
    (extra L - D = snake at the child end, legal there).  Fewest stages n >= ceil(L / rep) whose equal positions,
    snapped out of keepouts to the nearer edge, keep every stage <= rep (balanced stages, no stubs); if no n up to
    +4 does, the greedy edge-snap below (a stage over rep only where a keepout is longer than rep)."""
    n0 = max(1, math.ceil(L / rep - 1e-6))
    if iv and L > D + 1e-6 and iv[-1][1] >= D - 1e-6:
        # the child itself sits inside a keepout (e.g. a macro clock pin): the snake tail is not legal either, so the
        # blocked interval runs to L and a repeater there snaps back to the keepout edge
        iv = [list(v) for v in iv[:-1]] + [[iv[-1][0], L]]
        D = L
    if not iv or n0 == 1:
        if n0 == 1:
            return [L]
        return [L / n0] * n0
    for n in range(n0, n0 + 5):
        pos = _snap(D, L, iv, rep, n)
        if pos is not None:
            st = [y - x for x, y in zip([0.0] + pos, pos + [L])]
            if max(st) <= rep + 1e-6:
                return [v for v in st if v > 1e-6] or [L]
    return _place_greedy(D, L, iv, rep)


def _place_greedy(D, L, iv, rep):
    """stage lengths for a wire of total length L >= D whose first D um follow a route with blocked intervals iv
    (extra L - D = snake at the child end, legal there).  Equal spacing; an ideal site inside a keepout snaps back to
    its edge if the stage stays <= rep, else forward."""
    pos, prev = [], 0.0
    guard = 0
    while guard < 10000:
        guard += 1
        n = math.ceil((L - prev) / rep - 1e-6)
        if n <= 1:
            break
        s = prev + (L - prev) / n
        v = next((v for v in iv if v[0] < s < v[1]), None) if s < D else None
        if v is not None:
            back, fwd = v[0] - EPS, v[1] + EPS
            if back > prev + 1.0 and (fwd - prev > rep or s - back <= fwd - s):
                s = back
            else:
                s = min(fwd, L - 1e-6) if fwd < L else fwd
                if s >= L:
                    break
        pos.append(s)
        prev = s
    st = [y - x for x, y in zip([0.0] + pos, pos + [L])]
    return [v for v in st if v > 1e-6] or [max(L, 0.0)]


def edge_delay(M, c, sl, sib=None, sink=False):
    """delay of one tree edge with exact stage lengths sl (same formula as mscts.legal.arrivals_seg): the driving
    cell sees its own first segment plus the sibling's first segment (2-load node)."""
    d0, k1, k2 = M.k[c]
    ks = M.ks[c]
    first = sl[0] + (sib[0] if sib else 0.0)
    t = d0 + k1 * first + k2 * sl[0] ** 2 + ks * sl[0] + sum(M.seg_ps(x, c) for x in sl[1:])
    if sink and sib is not None:
        t -= ks * sl[-1]
    return t
