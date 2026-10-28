"""opentools.mscts placement legality: clock buffer sites outside keepouts (hard cores + halo, PHY, streets that are
reserved for other classes), as DATA (rects); no PDK knowledge here.

    L = Legality(keepouts=[[x0, y0, x1, y1], ...], inside=[[...]]?)    inside = allowed area (e.g. partitions), optional
    L.ok(xy)                                   buffer site legal?
    L.nearest_on_path(a, b, s, D)              nearest legal arc position to s on the x-first L path a -> b (or None)
    legalize_repeaters(R, L)                   per tree edge: repeaters slid out of keepouts -> actual stage lengths
    arrivals_seg(R, segs, corner)              model arrivals with those actual stage lengths
"""
import math

from .region import _lpoint, _man


class Legality:
    def __init__(self, keepouts=(), inside=None, bucket=250.0):
        self.k = [tuple(map(float, r[:4])) for r in keepouts]
        self.inside = [tuple(map(float, r[:4])) for r in inside] if inside else None
        self.b = bucket
        self.idx = {}
        for n, r in enumerate(self.k):
            for i in range(int(r[0] // bucket), int(r[2] // bucket) + 1):
                for j in range(int(r[1] // bucket), int(r[3] // bucket) + 1):
                    self.idx.setdefault((i, j), []).append(n)

    def hits(self, p):
        return [self.k[n] for n in self.idx.get((int(p[0] // self.b), int(p[1] // self.b)), ())
                if self.k[n][0] < p[0] < self.k[n][2] and self.k[n][1] < p[1] < self.k[n][3]]

    def ok(self, p):
        if self.inside is not None and not any(r[0] <= p[0] <= r[2] and r[1] <= p[1] <= r[3] for r in self.inside):
            return False
        return not self.hits(p)

    def blocked_intervals(self, a, b):
        """arc intervals [s0, s1] of the x-first L path a -> b that are inside a keepout."""
        out = []
        dx = abs(b[0] - a[0])
        for r in self.k:
            # x leg: y = a.y, x from a.x to b.x
            if r[1] < a[1] < r[3] and dx > 0:
                lo, hi = sorted((a[0], b[0]))
                x0, x1 = max(lo, r[0]), min(hi, r[2])
                if x1 > x0:
                    s0, s1 = abs(x0 - a[0]), abs(x1 - a[0])
                    out.append((min(s0, s1), max(s0, s1)))
            # y leg: x = b.x, y from a.y to b.y
            if r[0] < b[0] < r[2] and b[1] != a[1]:
                lo, hi = sorted((a[1], b[1]))
                y0, y1 = max(lo, r[1]), min(hi, r[3])
                if y1 > y0:
                    s0, s1 = dx + abs(y0 - a[1]), dx + abs(y1 - a[1])
                    out.append((min(s0, s1), max(s0, s1)))
        out.sort()
        m = []
        for s0, s1 in out:
            if m and s0 <= m[-1][1] + 1e-9:
                m[-1][1] = max(m[-1][1], s1)
            else:
                m.append([s0, s1])
        return m

    def nearest_on_path(self, a, b, s, D, eps=0.05):
        cands = [s] + [v for iv in self.blocked_intervals(a, b) for v in (iv[0] - eps, iv[1] + eps)] + [0.0, D]
        best = None
        for v in cands:
            if 0.0 <= v <= D and self.ok(_lpoint(a, b, v)):
                if best is None or abs(v - s) < abs(best - s):
                    best = v
        return best


def legalize_repeaters(R, L):
    """-> (segs {(node, kid): [stage lengths]}, ledger dict).
    Street mode (R.router, mscts.street): an edge keeps the exact stages chosen when it was merged (R.pre_segs) if its
    length is unchanged; any other edge (trunk legs, balanced leaf legs) is routed on the streets and repeated there.
    Legacy mode: ideal repeater positions at L/n spacing on the x-first L path; one inside a keepout slides to the
    nearest legal arc position (back first, then forward) between its neighbours."""
    rep, leg_max = R.M["rep_um"], R.M["leg_max_um"]
    router = getattr(R, "router", None)
    pre = getattr(R, "pre_segs", None) or {}
    segs, moved, worst = {}, 0, 0.0
    for nd in R.nodes:
        for k, Lk, sn in nd["kids"]:
            a, b = nd["xy"], R.nodes[k]["xy"]
            D = _man(a, b)
            if router is not None:
                ps = pre.get((nd["id"], k))
                if ps is not None and abs(sum(ps) - Lk) < 1e-6:
                    st = list(ps)
                else:
                    from .street import place, plen
                    pts, iv, _ = router.route(a, b)
                    R.routes[(nd["id"], k)] = pts
                    D = plen(pts)                        # > Manhattan only on a jog route
                    st = place(D, max(Lk, D), iv, rep)
                segs[(nd["id"], k)] = st
                worst = max(worst, max(st))
                continue
            n = max(1, math.ceil(Lk / rep - 1e-9))
            pos = []
            prev = 0.0
            for r in range(1, n):
                s = Lk * r / n
                sp = min(s, D)
                if L is not None and not L.ok(_lpoint(a, b, sp)):
                    v = L.nearest_on_path(a, b, sp, D)
                    if v is not None and v > prev:
                        s = v + (s - sp)
                        moved += 1
                pos.append(s)
                prev = min(s, D)
            st = [y - x for x, y in zip([0.0] + pos, pos + [Lk])]
            segs[(nd["id"], k)] = st
            worst = max(worst, max(st))
    allst = [x for v in segs.values() for x in v]
    over = sum(1 for x in allst if x > leg_max + 1e-6)
    return segs, dict(repeaters_moved=moved, max_stage_um=round(worst, 1), stages_over_leg_max=over, leg_max_um=leg_max,
                      stages=len(allst), stages_over_rep=sum(1 for x in allst if x > rep + 1e-6), rep_um=rep,
                      street=router is not None)


def arrivals_seg(R, segs, corner):
    """model arrival at every node from the root with the ACTUAL stage lengths (same stage model as RegionTree)."""
    M = R.M
    d0, k1, k2 = M.k[corner]
    ks = M.ks[corner]
    arr = {R.root: 0.0}
    st = [R.root]
    while st:
        n = st.pop()
        kids = R.nodes[n]["kids"]
        firsts = [segs[(n, k)][0] for k, _, _ in kids]
        for (k, _, _), sl in zip(kids, (segs[(n, k)] for k, _, _ in kids)):
            sink = R.nodes[k]["kind"] == "sink"
            if len(kids) == 2:
                t = d0 + k1 * sum(firsts) + k2 * sl[0] ** 2 + ks * sl[0]
            else:
                t = d0 + k1 * sl[0] + k2 * sl[0] ** 2 + ks * sl[0]
            t += sum(M.seg_ps(x, corner) for x in sl[1:])
            if sink and len(kids) == 2:
                t -= ks * sl[-1]
            arr[k] = arr[n] + t
            st.append(k)
    return arr


def _edge_ps(R, n, k, segs, corner):
    M = R.M
    d0, k1, k2 = M.k[corner]
    ks = M.ks[corner]
    kids = R.nodes[n]["kids"]
    sl = segs[(n, k)]
    first = sum(segs[(n, q)][0] for q, _, _ in kids) if len(kids) == 2 else sl[0]
    t = d0 + k1 * first + k2 * sl[0] ** 2 + ks * sl[0] + sum(M.seg_ps(x, corner) for x in sl[1:])
    if len(kids) == 2 and R.nodes[k]["kind"] == "sink":
        t -= ks * sl[-1]
    return t


def _extend(sl, e, rep):
    tail = sl[-1] + e
    n = max(1, math.ceil(tail / rep - 1e-9))
    return sl[:-1] + [tail / n] * n


def rebalance(R, corner="TT", iters=3):
    """after legalize_repeaters: re-balance every 2-load node bottom-up by lengthening the FASTER child's edge at its
    child end (snake, ledgered in R.snakes kind 'legal_rebalance'), so the slid repeaters leave no skew.
    -> total added snake um."""
    rep = R.M["rep_um"]
    par = {}
    for nd in R.nodes:
        for k, _, _ in nd["kids"]:
            par[k] = nd["id"]
    order = []
    st = [R.root]
    while st:
        n = st.pop()
        order.append(n)
        st += [k for k, _, _ in R.nodes[n]["kids"]]
    added = 0.0
    for _ in range(iters):
        below = {}
        for n in reversed(order):
            nd = R.nodes[n]
            if nd["kind"] == "sink":
                below[n] = nd.get("ins", {}).get(corner, 0.0)
                continue
            kids = nd["kids"]
            if not kids:
                below[n] = 0.0
                continue
            if len(kids) == 2:
                (a, _, _), (b, _, _) = kids
                ta = _edge_ps(R, n, a, R.segs, corner) + below[a]
                tb = _edge_ps(R, n, b, R.segs, corner) + below[b]
                if abs(ta - tb) > 0.2:
                    f = b if ta > tb else a
                    tgt = max(ta, tb)
                    base = list(R.segs[(n, f)])
                    lo, hi = 0.0, 20000.0
                    for _ in range(50):
                        mid = (lo + hi) / 2
                        R.segs[(n, f)] = _extend(base, mid, rep)
                        if _edge_ps(R, n, f, R.segs, corner) + below[f] < tgt:
                            lo = mid
                        else:
                            hi = mid
                    R.segs[(n, f)] = _extend(base, hi, rep)
                    added += hi
                    R.snakes.append(dict(at=list(R.nodes[f]["xy"]), side=R.nodes[f].get("name", f), um=round(hi, 1),
                                         kind="legal_rebalance"))
            below[n] = max(_edge_ps(R, n, k, R.segs, corner) + below[k] for k, _, _ in kids)
    return round(added, 1)
