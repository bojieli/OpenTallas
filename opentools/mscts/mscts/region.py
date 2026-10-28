"""opentools.mscts REGION MODE: build one region's clock tree with a late-split objective (METHODOLOGY 12.13b).

Bottom-up zero-skew merging (DME-style on Manhattan L paths, buffered):
  * every cluster has a root = a clock buffer input pin at xy, and t = predicted delay from that pin to its sinks;
  * merging clusters i, j places a new buffer M on the L path between their roots so that
        branch(M -> i) + t_i == branch(M -> j) + t_j,   branch = pair_ps: the node's cell sees both first segments' load, each side its own RC
    (bisection on the split point).  If no split point balances them, M sits at the slower root's side and the faster
    side gets a SNAKE (extra wire length e that balances the pair), reported in the ledger
    (v5.1: meander allowed sparsely, after the structural fix);
  * every branch of length L is repeated with ceil(L / rep_um) equal segments (repeaters on the path).
Merge order = the objective:
  * 'nearest'    : plain geometric nearest-pair merging (baseline, no crossing knowledge);
  * 'late_split' : cost = Manhattan distance - bonus * (number of listed crossing pairs that the merge joins), so pairs
                   that exchange data meet LOW in the tree: their last common buffer is close, the unshared clock is
                   small.  The objective value reported is the max / mean unshared delay over the listed pairs.
The region root is driven from the feed entry (a neighbour-forwarded feed or a spine tap) with one repeated leg.
Outputs: cells, wires (driver -> load, length, route), per-sink model arrival, per-crossing LCA / unshared / derated
margin (clkplan.ocv, shared model), snake ledger.  netlist.py turns it into SPICE + Verilog/SPEF for verification.
Placement legality: build(legal=mscts.legal.Legality) keeps every merge buffer on a legal site (moved along its L
path, re-balanced by a ledgered snake); legal.legalize_repeaters() slides repeaters out of keepouts and reports the
stage lengths; trunk.py composes a FIXED trunk on allocated tracks (opentools.metal / a row reservation) with
mscts local trees below its leaves.
"""
import math


def _man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _lpoint(a, b, s):
    """point at Manhattan distance s from a along the x-first L path a -> b."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    if s <= abs(dx):
        return (a[0] + math.copysign(s, dx) if dx else a[0], a[1])
    s2 = s - abs(dx)
    return (b[0], a[1] + (math.copysign(s2, dy) if dy else 0.0))


class RegionTree:
    def __init__(self, model, corner="TT", legal=None, street=True):
        self.M, self.c = model, corner
        self.nodes = []            # dict(id, xy, kind sink|merge|root, kids[(node, L_um, snake_um)], t_ps, sink?)
        self.snakes = []
        self.legal = legal         # mscts.legal.Legality (buffer sites) or None
        self.moved = []            # merge points moved off an illegal site
        # street-aware routing (mscts.street, OSS-CLOCK-3): with a Legality, wires follow legal streets and merge
        # buffers take a legal point of their merging segment; exact stage lengths per edge in pre_segs
        self.router = None
        if legal is not None and street:
            from .street import Router
            self.router = Router(legal, model["rep_um"])
            self._xe = sorted({v for r in legal.k for v in (r[0] - 0.05, r[2] + 0.05)})
            self._ye = sorted({v for r in legal.k for v in (r[1] - 0.05, r[3] + 0.05)})
        self.routes = {}           # (parent, kid) -> polyline parent .. kid (street mode)
        self.pre_segs = {}         # (parent, kid) -> exact stage lengths chosen at build time (street mode)
        self.detours = []          # balanced off-box merge points (street mode): extra route wire, both sides

    def branch_ps(self, L, two_loads=False):
        return self.M.wire_ps(L, self.c)

    def pair_ps(self, La, Lb, c=None, sink_a=False, sink_b=False):
        """delays from a 2-load node's input to each child's input: the node's own cell sees BOTH first segments
        (d0 + k1 (la + lb)), each side then has its own wire RC k2 l^2 and n - 1 further repeated segments."""
        c = c or self.c
        d0, k1, k2 = self.M.k[c]
        rep = self.M["rep_um"]

        def split(L):
            n = max(1, math.ceil(L / rep - 1e-9))
            return n, L / n
        na, la = split(La)
        nb, lb = split(Lb)
        first = d0 + k1 * (la + lb)
        ks = self.M.ks[c]
        # ks l: the input slew a segment of length l gives the NEXT cell (repeater, or the child root unless a sink pin)
        return (first + k2 * la * la + (na - 1) * self.M.seg_ps(la, c) + (0.0 if sink_a else ks * la),
                first + k2 * lb * lb + (nb - 1) * self.M.seg_ps(lb, c) + (0.0 if sink_b else ks * lb))

    def merge_street(self, i, j):
        return _merge_street(self, i, j)

    def add(self, **kw):
        kw["id"] = len(self.nodes)
        self.nodes.append(kw)
        return kw["id"]

    def merge(self, i, j):
        if self.router is not None:
            return self.merge_street(i, j)
        a, b = self.nodes[i], self.nodes[j]
        D = _man(a["xy"], b["xy"])
        ta, tb = a["t_ps"], b["t_ps"]

        sa, sb = a["kind"] == "sink", b["kind"] == "sink"

        def f(La, Lb):         # > 0 when side a is slower
            da, db = self.pair_ps(La, Lb, sink_a=sa, sink_b=sb)
            return (da + ta) - (db + tb)

        def solve(g, lo, hi):  # g increasing, g(lo) < 0 <= g(hi)
            for _ in range(60):
                mid = (lo + hi) / 2
                if g(mid) < 0:
                    lo = mid
                else:
                    hi = mid
            return (lo + hi) / 2
        snake, side = 0.0, None
        if f(0.0, D) >= 0:                   # a slower even with M on a: M at a, snake on b
            x = 0.0
            Lb = solve(lambda L: -f(0.0, L), D, D + 20000.0) if -f(0.0, D) < 0 else D
            La, snake, side = 0.0, Lb - D, j
        elif f(D, 0.0) <= 0:                 # b slower: M at b, snake on a
            x = D
            La = solve(lambda L: f(L, 0.0), D, D + 20000.0) if f(D, 0.0) < 0 else D
            Lb, snake, side = 0.0, La - D, i
        else:
            x = solve(lambda t: f(t, D - t), 0.0, D)
            La, Lb = x, D - x
        if self.legal is not None and not self.legal.ok(_lpoint(a["xy"], b["xy"], x)):
            # placement legality: the merge buffer moves to the nearest legal site ON the L path; the pair is then
            # re-balanced with a snake on the faster side (ledgered), never by an illegal buffer
            x2 = self.legal.nearest_on_path(a["xy"], b["xy"], x, D)
            if x2 is not None and abs(x2 - x) > 1e-6:
                self.moved.append(dict(at=list(_lpoint(a["xy"], b["xy"], x)), to=list(_lpoint(a["xy"], b["xy"], x2)),
                                       um=round(abs(x2 - x), 1)))
                x, La, Lb, snake, side = x2, x2, D - x2, 0.0, None
                g = f(La, Lb)
                if g > 1e-9:                     # a slower: lengthen b
                    Lb = solve(lambda L: -f(La, L), Lb, Lb + 20000.0)
                    snake, side = Lb - (D - x2), j
                elif g < -1e-9:
                    La = solve(lambda L: f(L, Lb), La, La + 20000.0)
                    snake, side = La - x2, i
        xy = _lpoint(a["xy"], b["xy"], x)
        da, db = self.pair_ps(La, Lb, sink_a=sa, sink_b=sb)
        t = max(da + ta, db + tb)
        if snake > 1e-6:
            self.snakes.append(dict(at=list(xy), side=self.nodes[side].get("name", side), um=round(snake, 1)))
        return self.add(xy=xy, kind="merge", kids=[(i, La, snake if side == i else 0.0), (j, Lb, snake if side == j else 0.0)],
                        t_ps=t)


def _street_side(R, p, q, L=None):
    """route p -> q on the streets, stage lengths for total wire L (default the route length)."""
    from .street import place, plen
    pts, iv, _ = R.router.route(p, q)
    D = plen(pts)
    return pts, place(D, D if L is None else max(L, D), iv, R.M["rep_um"])


def _model_split(R, A, B, ta, tb, sa, sb):
    """zero-skew split x (um from A) of the equal-stage model, clamped to [0, D]."""
    D = _man(A, B)

    def fm(t):
        da, db = R.pair_ps(t, D - t, sink_a=sa, sink_b=sb)
        return (da + ta) - (db + tb)
    if fm(0.0) >= 0:
        return 0.0, fm
    if fm(D) <= 0:
        return D, fm
    lo, hi = 0.0, D
    for _ in range(50):
        mid = (lo + hi) / 2
        if fm(mid) < 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2, fm


def _seg_us(R, A, B, x):
    """candidate positions u (x-offset from A) on the merging segment at split x: its ends + keepout-edge crossings."""
    dx, dy = B[0] - A[0], B[1] - A[1]
    sx, sy = (1.0 if dx >= 0 else -1.0), (1.0 if dy >= 0 else -1.0)
    lo, hi = max(0.0, x - abs(dy)), min(x, abs(dx))
    us = {lo, hi}
    us.update((X - A[0]) * sx for X in R._xe if lo < (X - A[0]) * sx < hi)
    us.update(x - (Y - A[1]) * sy for Y in R._ye if lo < x - (Y - A[1]) * sy < hi)
    return [(u, (A[0] + sx * u, A[1] + sy * (x - u))) for u in sorted(us, key=lambda u: abs(u - hi))], hi


def _detour_pts(R, A, B, x, hmax):
    """legal points OFF the bounding box that still balance split x: |p - A| = x + h, |p - B| = D - x + h (both
    routes grow by the same detour h, classic DME around an obstacle).  Candidates on keepout edge lines just outside
    the box, -> [(h, p)] sorted by h, h <= hmax."""
    x0b, x1b = min(A[0], B[0]), max(A[0], B[0])
    y0b, y1b = min(A[1], B[1]), max(A[1], B[1])
    out = []
    for Y in R._ye:
        if Y > y1b:
            h, r = Y - y1b, x - (y1b - A[1])
        elif Y < y0b:
            h, r = y0b - Y, x - (A[1] - y0b)
        else:
            continue
        if h > hmax or r < -1e-9:
            continue
        sx = 1.0 if B[0] >= A[0] else -1.0
        px = A[0] + sx * r
        if x0b - 1e-6 <= px <= x1b + 1e-6:
            out.append((h, (px, Y)))
    for X in R._xe:
        if X > x1b:
            h, r = X - x1b, x - (x1b - A[0])
        elif X < x0b:
            h, r = x0b - X, x - (A[0] - x0b)
        else:
            continue
        if h > hmax or r < -1e-9:
            continue
        sy = 1.0 if B[1] >= A[1] else -1.0
        py = A[1] + sy * r
        if y0b - 1e-6 <= py <= y1b + 1e-6:
            out.append((h, (X, py)))
    return sorted(((h, p) for h, p in out if R.legal.ok(p)), key=lambda v: v[0])


def _split_cands(R, A, B, x0):
    """split positions to try when the merging segment at x0 has no legal point: keepout-edge crossings of the two L
    paths A -> B, nearest to x0 first."""
    D = _man(A, B)
    out = set()
    for pts in ([A, (B[0], A[1]), B], [A, (A[0], B[1]), B]):
        for a, b in R.router.blocked(pts, R.router.kos(A, B)):
            out.update((a - 0.05, b + 0.05))
    return sorted((v for v in out if 0.0 <= v <= D), key=lambda v: abs(v - x0))


def _blocked_penalty(R, i, j):
    """merge-order cost term (street mode): estimated snake (um) when the zero-skew point of i, j has no legal
    merge site = 2 x distance to the nearest legal split (0 when legal)."""
    a, b = R.nodes[i], R.nodes[j]
    A, B = a["xy"], b["xy"]
    x0, _ = _model_split(R, A, B, a["t_ps"], b["t_ps"], a["kind"] == "sink", b["kind"] == "sink")
    if any(R.legal.ok(p) for _, p in _seg_us(R, A, B, x0)[0]):
        return 0.0
    pen = 2.0 * _man(A, B)
    for x in _split_cands(R, A, B, x0):
        if any(R.legal.ok(p) for _, p in _seg_us(R, A, B, x)[0]):
            pen = 2.0 * abs(x - x0)
            break
    dt = _detour_pts(R, A, B, x0, pen / 2.0)
    return min(pen, 2.0 * dt[0][0]) if dt else pen


def _merge_street(R, i, j):
    """street-mode zero-skew merge: split x along the Manhattan distance solved on EXACT stage lengths of the street
    routes (secant + bisection); the merge buffer at the legal point of the merging segment with the best routes;
    a residual (no balancing split inside [0, D], or a placement step) -> snake on the faster side (ledgered)."""
    from .street import edge_delay, place, plen
    a, b = R.nodes[i], R.nodes[j]
    A, B = a["xy"], b["xy"]
    D = _man(A, B)
    ta, tb = a["t_ps"], b["t_ps"]
    sa, sb = a["kind"] == "sink", b["kind"] == "sink"
    M, c, rep = R.M, R.c, R.M["rep_um"]
    dx, dy = B[0] - A[0], B[1] - A[1]
    sx, sy = (1.0 if dx >= 0 else -1.0), (1.0 if dy >= 0 else -1.0)
    ax, ay = abs(dx), abs(dy)

    def pick(x):
        cands, hi = _seg_us(R, A, B, x)
        best = None
        for u, p in cands[:16]:
            if not R.legal.ok(p):
                continue
            ra, ia, ka = R.router.route(p, A)
            rb, ib, kb = R.router.route(p, B)
            key = (max(ka[0], kb[0]), max(ka[2], kb[2]), ka[1] + kb[1], abs(u - hi))
            if best is None or key < best[0]:
                best = (key, p, (ra, ia), (rb, ib))
        if best is None and det[0]:
            # no legal point on the merging segment: a balanced detour point (both sides + h) if it costs less wire
            # than shifting the split to the nearest legal site (snake ~ 2 x shift)
            sn = next((2.0 * abs(xx - x) for xx in _split_cands(R, A, B, x)
                       if any(R.legal.ok(q) for _, q in _seg_us(R, A, B, xx)[0])), 2.0 * D)
            for h, p in _detour_pts(R, A, B, x, sn / 2.0)[:4]:
                ra, ia, ka = R.router.route(p, A)
                rb, ib, kb = R.router.route(p, B)
                key = (max(ka[0], kb[0]), h, max(ka[2], kb[2]), ka[1] + kb[1])
                if best is None or key < best[0]:
                    best = (key, p, (ra, ia), (rb, ib))
        return best

    det = [True]
    combo = [(0, 0)]

    def _rp(L, ex):
        # spacing with ex EXTRA repeaters: the stage-count step of a repeated wire is a delay jump (up to ~20 ps at a
        # 2-load node); one extra repeater on one side makes the balance reachable across that jump
        if ex <= 0 or L <= 0:
            return rep
        return min(rep, L / (max(1, math.ceil(L / rep - 1e-6)) + ex) + 1e-9)

    def ev(x):
        pk = pick(x)
        if pk is None:
            return None
        _, p, (ra, ia), (rb, ib) = pk
        xa, xb = combo[0]
        Pa, Pb = plen(ra), plen(rb)              # = x, D - x on the merging segment; + h each on a detour point (+ jogs)
        la, lb = place(Pa, Pa, ia, _rp(Pa, xa)), place(Pb, Pb, ib, _rp(Pb, xb))
        da, db = edge_delay(M, c, la, lb, sa), edge_delay(M, c, lb, la, sb)
        return (da + ta) - (db + tb), p, ra, rb, la, lb, ia, ib, x
    # model split (equal stages) as the starting point
    def fm(t):
        da, db = R.pair_ps(t, D - t, sink_a=sa, sink_b=sb)
        return (da + ta) - (db + tb)
    if fm(0.0) >= 0:
        x0 = 0.0
    elif fm(D) <= 0:
        x0 = D
    else:
        lo, hi = 0.0, D
        for _ in range(60):
            mid = (lo + hi) / 2
            if fm(mid) < 0:
                lo = mid
            else:
                hi = mid
        x0 = (lo + hi) / 2
    best = None
    tried = {}

    def run(x):
        x = min(max(x, 0.0), D)
        k = (combo[0], round(x, 4))
        if k not in tried:
            tried[k] = ev(x)
        return tried[k]
    x_model = x0
    for combo_ in ((0, 0), (1, 0), (0, 1)):
        combo[0] = combo_
        x0 = x_model
        e0 = run(x0)
        if e0 is None:                           # model split point has no legal merging-segment point: nearest legal split
            for xx in _split_cands(R, A, B, x0):
                if run(xx) is not None:
                    x0, e0 = xx, run(xx)
                    break
        pts = [(x0, e0)]
        if e0 is not None and abs(e0[0]) > 0.3 and 0.0 < x0 < D:
            # bracket and bisect on the exact delays (piecewise continuous in x)
            slope = max(1e-3, (fm(min(D, x0 + 1.0)) - fm(max(0.0, x0 - 1.0))) / (min(D, x0 + 1.0) - max(0.0, x0 - 1.0)))
            x1 = x0 - e0[0] / slope
            e1 = run(x1)
            lo = hi = None
            for x, e in ((x0, e0), (min(max(x1, 0.0), D), e1)):
                if e is None:
                    continue
                if e[0] < 0 and (lo is None or x > lo[0]):
                    lo = (x, e)
                if e[0] >= 0 and (hi is None or x < hi[0]):
                    hi = (x, e)
            step = abs(x1 - x0) + 5.0
            k = 0
            while (lo is None or hi is None) and k < 12:
                k += 1
                x = (hi[0] - step) if lo is None else (lo[0] + step)
                x = min(max(x, 0.0), D)
                e = run(x)
                if e is not None:
                    if e[0] < 0:
                        lo = (x, e)
                    else:
                        hi = (x, e)
                if x in (0.0, D):
                    break
                step *= 2
            if lo is not None and hi is not None:
                for _ in range(30):
                    if abs(lo[1][0]) < 0.3 or abs(hi[1][0]) < 0.3 or hi[0] - lo[0] < 0.01:
                        break
                    xm = (lo[0] + hi[0]) / 2
                    e = run(xm)
                    if e is None:
                        break
                    if e[0] < 0:
                        lo = (xm, e)
                    else:
                        hi = (xm, e)
                pts += [lo, hi]
            else:
                pts += [v for v in (lo, hi) if v]
        if min((abs(v[0]) for v in tried.values() if v is not None), default=1e9) <= 0.3:
            break
    cand = [(e[-1], e) for e in tried.values() if e is not None]
    if not cand:
        # no legal point on any tried merging segment: legacy L-path move + snake
        router, R.router = R.router, None
        try:
            return R.merge(i, j)
        finally:
            R.router = router
    x, e = min(cand, key=lambda xe_: abs(xe_[1][0]))
    g, p, ra, rb, la, lb, ia, ib, _ = e
    snake, side = 0.0, None
    if abs(g) > 0.3:                        # residual: snake on the faster side, exact stages
        f_side = j if g > 0 else i
        Dside = plen(rb) if f_side == j else plen(ra)
        ivs = ib if f_side == j else ia
        other = la if f_side == j else lb
        tf, to = (tb, ta) if f_side == j else (ta, tb)
        sk_f, sk_o = (sb, sa) if f_side == j else (sa, sb)
        target = edge_delay(M, c, other, None, False)  # placeholder, recomputed below

        def dlt(ext):
            sl = place(Dside, Dside + ext, ivs, rep)
            return edge_delay(M, c, sl, other, sk_f) + tf - (edge_delay(M, c, other, sl, sk_o) + to), sl
        lo_, hi_ = 0.0, 20000.0
        for _ in range(50):
            mid = (lo_ + hi_) / 2
            if dlt(mid)[0] < 0:
                lo_ = mid
            else:
                hi_ = mid
        snake = min((lo_, hi_), key=lambda v: abs(dlt(v)[0]))
        sl = dlt(snake)[1]
        if f_side == j:
            lb = sl
        else:
            la = sl
        side = f_side
        del target
    La, Lb = sum(la), sum(lb)
    da, db = edge_delay(M, c, la, lb, sa), edge_delay(M, c, lb, la, sb)
    t = max(da + ta, db + tb)
    if snake > 1e-6:
        R.snakes.append(dict(at=list(p), side=R.nodes[side].get("name", side), um=round(snake, 1)))
    dtr = plen(ra) + plen(rb) - D
    if dtr > 1e-6:
        R.detours.append(dict(at=list(p), um=round(dtr, 1)))
    m = R.add(xy=tuple(p), kind="merge", kids=[(i, La, snake if side == i else 0.0), (j, Lb, snake if side == j else 0.0)],
              t_ps=t)
    R.routes[(m, i)], R.routes[(m, j)] = ra, rb
    R.pre_segs[(m, i)], R.pre_segs[(m, j)] = la, lb
    return m


def build(sinks, model, entry_xy, crossings=(), objective="late_split", bonus_um=None, corner="TT", legal=None,
          street=True):
    """sinks = [dict(name, xy, insertion_ps{TT,FF}?)], crossings = [(a, b)] sink names.  -> RegionTree with .root
    A sink's insertion_ps (its own internal clock insertion, e.g. a hard core's signed view) is balanced: the tree
    targets equal LATENCY (tree arrival + insertion), early taps for late cores (METHODOLOGY v5.0)."""
    R = RegionTree(model, corner, legal, street=street)
    bonus = bonus_um if bonus_um is not None else 4.0 * model["rep_um"]
    act = {}
    member = {}
    for s in sinks:
        ins = {k: float(v) for k, v in (s.get("insertion_ps") or {}).items()}
        n = R.add(xy=tuple(s["xy"]), kind="sink", kids=[], t_ps=ins.get(corner, 0.0), name=s["name"], ins=ins)
        act[n] = {s["name"]}
        member[s["name"]] = n
    partners = {}
    for a, b in crossings:
        if a in member and b in member:
            partners.setdefault(a, set()).add(b)
            partners.setdefault(b, set()).add(a)
    unit = model["rep_um"] * 0.5 / max(1e-9, model.wire_ps(model["rep_um"], corner))

    def cost(i, j):
        D_ = _man(R.nodes[i]["xy"], R.nodes[j]["xy"])
        dt_ = abs(R.nodes[i]["t_ps"] - R.nodes[j]["t_ps"]) * unit
        # street mode: merge cost = the wire the merge needs incl. its balancing snake (max(D, 2 unit dt)) + the
        # blocked-site penalty; legacy: D + unit dt
        c = max(D_, 2.0 * dt_) if R.router is not None else D_ + dt_
        if objective == "late_split" and partners:
            si, sj = (act[i], act[j]) if len(act[i]) <= len(act[j]) else (act[j], act[i])
            c -= bonus * sum(len(partners.get(x, set()) & sj) for x in si)
        if R.router is not None:
            c += _blocked_penalty(R, i, j)
        return c
    C = {}
    ids = list(act)
    for u in range(len(ids)):
        for v in range(u + 1, len(ids)):
            C[(ids[u], ids[v])] = cost(ids[u], ids[v])
    while len(act) > 1:
        (i, j), _ = min(C.items(), key=lambda kv: kv[1])
        m = R.merge(i, j)
        act[m] = act.pop(i) | act.pop(j)
        C = {k: v for k, v in C.items() if i not in k and j not in k}
        for o in act:
            if o != m:
                C[(o, m)] = cost(o, m)
    top = next(iter(act))
    L = _man(entry_xy, R.nodes[top]["xy"])
    R.root = R.add(xy=tuple(entry_xy), kind="root", kids=[(top, L, 0.0)], t_ps=R.branch_ps(L, False) + R.nodes[top]["t_ps"])
    if R.router is not None:
        from .street import edge_delay
        pts, sl = _street_side(R, tuple(entry_xy), R.nodes[top]["xy"])
        R.routes[(R.root, top)], R.pre_segs[(R.root, top)] = pts, sl
        R.nodes[R.root]["t_ps"] = edge_delay(R.M, corner, sl) + R.nodes[top]["t_ps"]
    return R


def arrivals(R, corner=None):
    """model arrival (ps) at every node's buffer input from the root buffer input, and parent links."""
    c = corner or R.c
    arr, par = {R.root: 0.0}, {R.root: None}
    st = [R.root]
    while st:
        n = st.pop()
        kids = R.nodes[n]["kids"]
        if len(kids) == 2:
            ds = R.pair_ps(kids[0][1], kids[1][1], c, sink_a=R.nodes[kids[0][0]]["kind"] == "sink",
                           sink_b=R.nodes[kids[1][0]]["kind"] == "sink")
        else:
            ds = [R.M.wire_ps(L, c) for _, L, _ in kids]
        for (k, L, sn), dk in zip(kids, ds):
            arr[k] = arr[n] + dk
            par[k] = n
            st.append(k)
    if getattr(R, "segs", None):                 # legalized repeaters: actual stage lengths (mscts.legal)
        from .legal import arrivals_seg
        arr = arrivals_seg(R, R.segs, c)
    return arr, par


def segments(R):
    """explicit buffered netlist graph: [(drv_buf, load_buf, wire_um)] + buffer list [(name, xy, kind)].
    Every tree node is a buffer (sink nodes = the leaf buffer at the sink); a kid edge of length L gets
    n = ceil(L / rep_um) - 1 repeaters at equal spacing on the L path."""
    from .street import at as _at, sub as _sub
    bufs = {}
    edges = []
    pts = {}
    rep = R.M["rep_um"]

    def bname(n):
        nd = R.nodes[n]
        return nd.get("name") and f"s_{nd['name']}" or f"{nd['kind'][0]}{n}"
    for nd in R.nodes:
        bufs[bname(nd["id"])] = (nd["xy"], nd["kind"])
    for nd in R.nodes:
        for k, L, sn in nd["kids"]:
            sg = (getattr(R, "segs", None) or {}).get((nd["id"], k))
            if sg is None:
                n = max(1, math.ceil(L / rep - 1e-9))
                sg = [L / n] * n
            prev = bname(nd["id"])
            a, b = nd["xy"], R.nodes[k]["xy"]
            route = (getattr(R, "routes", None) or {}).get((nd["id"], k)) or [a, (b[0], a[1]), b]
            D = _man(a, b)
            s = 0.0
            for r, ln in enumerate(sg[:-1], 1):
                s0, s = s, s + ln
                nm = f"r{nd['id']}_{k}_{r}"
                bufs[nm] = (_at(route, min(s, D)), "rep")
                edges.append((prev, nm, ln))
                pts[(prev, nm)] = _sub(route, min(s0, D), min(s, D))
                prev = nm
            edges.append((prev, bname(k), sg[-1]))
            pts[(prev, bname(k))] = _sub(route, min(s, D), D)
    R.edge_pts = pts
    return bufs, edges


def lca_unshared(R, a, b, corner=None):
    """(lca node, unshared ps on a side, on b side, stages a, stages b) between two sink names."""
    arr, par = arrivals(R, corner)
    idx = {nd.get("name"): nd["id"] for nd in R.nodes if nd["kind"] == "sink"}
    ca, cb = [idx[a]], [idx[b]]
    while par[ca[-1]] is not None:
        ca.append(par[ca[-1]])
    while par[cb[-1]] is not None:
        cb.append(par[cb[-1]])
    sb = set(cb)
    l = next(x for x in ca if x in sb)
    rep = R.M["rep_um"]

    def stages(chain):
        n = 0
        for x in chain:
            if x == l:
                break
            p = par[x]
            L = next(L for k, L, _ in R.nodes[p]["kids"] if k == x)
            n += max(1, math.ceil(L / rep - 1e-9))
        return n
    return l, arr[idx[a]] - arr[l], arr[idx[b]] - arr[l], stages(ca), stages(cb)


def report(R, crossings, budget_ps, min_margin_ps=100.0, corners=("TT", "FF"), same_region=True):
    from clkplan import ocv
    T = R.M.T
    rows = []
    for a, b in crossings:
        row = dict(a=a, b=b)
        for c in corners:
            l, ua, ub, na, nb = lca_unshared(R, a, b, c)
            arr, _ = arrivals(R, c)
            idx = {nd.get("name"): nd["id"] for nd in R.nodes if nd["kind"] == "sink"}
            pts = [R.nodes[idx[a]]["xy"], R.nodes[idx[b]]["xy"], R.nodes[l]["xy"]]
            dist = math.hypot(max(p[0] for p in pts) - min(p[0] for p in pts), max(p[1] for p in pts) - min(p[1] for p in pts))
            ia, ib = (R.nodes[idx[a]].get("ins", {}).get(c, 0.0), R.nodes[idx[b]].get("ins", {}).get(c, 0.0))
            bra, brb = ocv.branch(T, c, ua, na, ia), ocv.branch(T, c, ub, nb, ib)
            d = arr[idx[b]] + ib - arr[idx[a]] - ia
            p_up, p_dn, der, mg = ocv.landed_margin(T, c, d, bra, brb, dist, same_region, budget_ps)
            row[c] = dict(unshared_ps=round(max(ua, ub), 1), d_ps=round(d, 1), derated_abs_ps=round(der, 1), margin_ps=round(mg, 1))
        rows.append(row)
    arrTT, _ = arrivals(R, "TT")
    sk = [arrTT[nd["id"]] for nd in R.nodes if nd["kind"] == "sink"]
    lat = [arrTT[nd["id"]] + nd.get("ins", {}).get("TT", 0.0) for nd in R.nodes if nd["kind"] == "sink"]
    out = dict(sinks=len(sk), insertion_TT_ps=round(max(sk), 1), tap_spread_TT_ps=round(max(sk) - min(sk), 1),
               skew_TT_ps=round(max(lat) - min(lat), 3), latency_TT_ps=round(max(lat), 1),
               snakes=len(R.snakes), snake_um=round(sum(s["um"] for s in R.snakes), 1), crossings=len(rows),
               moved_merges=len(R.moved))
    if rows:
        for c in corners:
            u = [r[c]["unshared_ps"] for r in rows]
            out[c] = dict(max_unshared_ps=max(u), mean_unshared_ps=round(sum(u) / len(u), 1),
                          worst_margin_ps=min(r[c]["margin_ps"] for r in rows),
                          under_min=sum(1 for r in rows if r[c]["margin_ps"] < min_margin_ps))
    return out, rows
