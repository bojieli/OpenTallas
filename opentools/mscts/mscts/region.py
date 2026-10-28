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
Placement legality (streets, islands, allocated tracks from opentools.metal) is NOT applied in this version.
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
    def __init__(self, model, corner="TT"):
        self.M, self.c = model, corner
        self.nodes = []            # dict(id, xy, kind sink|merge|root, kids[(node, L_um, snake_um)], t_ps, sink?)
        self.snakes = []

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

    def add(self, **kw):
        kw["id"] = len(self.nodes)
        self.nodes.append(kw)
        return kw["id"]

    def merge(self, i, j):
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
        xy = _lpoint(a["xy"], b["xy"], x)
        da, db = self.pair_ps(La, Lb, sink_a=sa, sink_b=sb)
        t = max(da + ta, db + tb)
        if snake > 1e-6:
            self.snakes.append(dict(at=list(xy), side=self.nodes[side].get("name", side), um=round(snake, 1)))
        return self.add(xy=xy, kind="merge", kids=[(i, La, snake if side == i else 0.0), (j, Lb, snake if side == j else 0.0)],
                        t_ps=t)


def build(sinks, model, entry_xy, crossings=(), objective="late_split", bonus_um=None, corner="TT"):
    """sinks = [dict(name, xy)], crossings = [(a, b)] sink names.  -> RegionTree with .root"""
    R = RegionTree(model, corner)
    bonus = bonus_um if bonus_um is not None else 4.0 * model["rep_um"]
    act = {}
    member = {}
    for s in sinks:
        n = R.add(xy=tuple(s["xy"]), kind="sink", kids=[], t_ps=0.0, name=s["name"])
        act[n] = {s["name"]}
        member[s["name"]] = n
    partners = {}
    for a, b in crossings:
        if a in member and b in member:
            partners.setdefault(a, set()).add(b)
            partners.setdefault(b, set()).add(a)
    unit = model["rep_um"] * 0.5 / max(1e-9, model.wire_ps(model["rep_um"], corner))

    def cost(i, j):
        c = _man(R.nodes[i]["xy"], R.nodes[j]["xy"]) + abs(R.nodes[i]["t_ps"] - R.nodes[j]["t_ps"]) * unit
        if objective == "late_split" and partners:
            si, sj = (act[i], act[j]) if len(act[i]) <= len(act[j]) else (act[j], act[i])
            c -= bonus * sum(len(partners.get(x, set()) & sj) for x in si)
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
    return arr, par


def segments(R):
    """explicit buffered netlist graph: [(drv_buf, load_buf, wire_um)] + buffer list [(name, xy, kind)].
    Every tree node is a buffer (sink nodes = the leaf buffer at the sink); a kid edge of length L gets
    n = ceil(L / rep_um) - 1 repeaters at equal spacing on the L path."""
    bufs = {}
    edges = []
    rep = R.M["rep_um"]

    def bname(n):
        nd = R.nodes[n]
        return nd.get("name") and f"s_{nd['name']}" or f"{nd['kind'][0]}{n}"
    for nd in R.nodes:
        bufs[bname(nd["id"])] = (nd["xy"], nd["kind"])
    for nd in R.nodes:
        for k, L, sn in nd["kids"]:
            n = max(1, math.ceil(L / rep - 1e-9))
            prev = bname(nd["id"])
            a, b = nd["xy"], R.nodes[k]["xy"]
            D = _man(a, b)
            for r in range(1, n):
                nm = f"r{nd['id']}_{k}_{r}"
                bufs[nm] = (_lpoint(a, b, D * r / n), "rep")
                edges.append((prev, nm, L / n))
                prev = nm
            edges.append((prev, bname(k), L / n))
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
            bra, brb = ocv.branch(T, c, ua, na, 0.0), ocv.branch(T, c, ub, nb, 0.0)
            d = arr[idx[b]] - arr[idx[a]]
            p_up, p_dn, der, mg = ocv.landed_margin(T, c, d, bra, brb, dist, same_region, budget_ps)
            row[c] = dict(unshared_ps=round(max(ua, ub), 1), d_ps=round(d, 1), derated_abs_ps=round(der, 1), margin_ps=round(mg, 1))
        rows.append(row)
    arrTT, _ = arrivals(R, "TT")
    sk = [arrTT[nd["id"]] for nd in R.nodes if nd["kind"] == "sink"]
    out = dict(sinks=len(sk), insertion_TT_ps=round(max(sk), 1), skew_TT_ps=round(max(sk) - min(sk), 3),
               snakes=len(R.snakes), snake_um=round(sum(s["um"] for s in R.snakes), 1), crossings=len(rows))
    if rows:
        for c in corners:
            u = [r[c]["unshared_ps"] for r in rows]
            out[c] = dict(max_unshared_ps=max(u), mean_unshared_ps=round(sum(u) / len(u), 1),
                          worst_margin_ps=min(r[c]["margin_ps"] for r in rows),
                          under_min=sum(1 for r in rows if r[c]["margin_ps"] < min_margin_ps))
    return out, rows
