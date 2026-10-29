"""DIE-QC-3 (10-27) opt-in die clock-tree helpers for die_trial.py (--clock-rc 1x, --legal-dme).

Two builder root causes found by DIE-QC-2 (claude/die-qc2-1027@6b961c850c):
 (i)  die_trial's model RC is the 2W2S NDR assumption (R / 2, C x 1.1 of the ASAP7 M8/M9 setRC), but the die clock is
      routed at 1x width (no NDR, as the HEAD/KV recipe): routed 334 ps/mm vs 199 ps/mm modelled.
      -> RC_1X = the ASAP7 platform setRC M8/M9 mean, and a BUFx24 stage model fitted by OpenSTA on 1x ladders
         (opentools/mscts calib chain set, fit below), times the OSS-CLOCK-2 ngspice slope (TT 1.0485 / FF 1.0552).
 (ii) the site pass moved tree nodes off hard cores AFTER the geometric balance, so sibling legs ended up unequal
      (path-length spread up to 783 um std slices / 1,518 um W5).
      -> legal_dme(): bottom-up deferred-merge embedding ON LEGAL SITES (the OSS-CLOCK-3 mscts street method: the merge
         point is a legal point chosen for equal delay to its children, not a slid ideal point).  Every movable node is
         re-placed, in post-order, at the legal site that minimises the delay spread of its own subtree (exact stages:
         the same repeater placement place_reps() that the netlist uses, the same stage model), latency as tie-break.
         Fixed nodes (spine / column, plan-reserved rows) stay.  No snakes, pads, trims or post-route values: the leg
         geometry IS the routed shortest path between placed buffers (GRT-faithful).
"""
import math
from collections import defaultdict

# ASAP7 platform setRC M8/M9 (kohm/um, fF/um), mean of the two layers, 1x width (no NDR)
RC_1X = ((8.44765e-3 + 8.89556e-3) / 2, (1.03962e-1 + 9.28446e-2) / 2)
# BUFx24 stage d = d0 + k1 L + k2 L^2 + ks L_in (ps, um): mscts.calib fit, OpenSTA 1x ladders R 8.672 ohm/um
# C 0.0984 fF/um (DIE-QC-3 intel2:/srv/opentallas-scratch2/claude/die-qc3-1027/cal1x, resid <= 4.0 / 3.9 ps)
STAGE_1X = {"TT": dict(d0=20.8281, k1=0.013984, k2=0.00033554, ks=0.089109),
            "FF": dict(d0=16.9068, k1=0.012687, k2=0.00032779, ks=0.063246)}
SPICE_SCALE = {"TT": 1.0485, "FF": 1.0552}       # OSS-CLOCK-2 asap7_bufx24_spice_cal.json slope


def stage_ps(L, Lin, corner="TT"):
    s = STAGE_1X[corner]
    return (s["d0"] + s["k1"] * L + s["k2"] * L * L + s["ks"] * Lin) * SPICE_SCALE[corner]


class FastSite:
    """memoised legality on a 0.54-um grid + a bucket index of the partition rects (SiteMap.in_part is a linear scan)."""
    def __init__(self, site, grid=0.54, bucket=500.0):
        self.s, self.g, self.b = site, grid, bucket
        self.cache = {}
        self.W, self.H = site.W, site.H
        self.pidx = defaultdict(list)
        for r in getattr(site, "parts", []):
            for i in range(int(r[0] // bucket), int(r[2] // bucket) + 1):
                for j in range(int(r[1] // bucket), int(r[3] // bucket) + 1):
                    self.pidx[(i, j)].append(r)

    def legal(self, q):
        k = (round(q[0] / self.g), round(q[1] / self.g))
        v = self.cache.get(k)
        if v is None:
            if hasattr(self.s, "hits") and hasattr(self.s, "parts"):
                m = 0.5
                v = not self.s.hits(q) and any(r[0] + m <= q[0] <= r[2] - m and r[1] + m <= q[1] <= r[3] - m
                                               for r in self.pidx.get((int(q[0] // self.b), int(q[1] // self.b)), ()))
            else:
                v = self.s.legal(q)
            self.cache[k] = v
        return v

    def nearest(self, p, axis=None):
        return self.s.nearest(p, axis)


def _lpath(p, q):
    """L route p -> q: horizontal (M8) at p.y first, then vertical (M9) at q.x (die_trial._leg_rects convention)."""
    return [p, (q[0], p[1]), q] if abs(p[0] - q[0]) > 1e-6 and abs(p[1] - q[1]) > 1e-6 else [p, q]


def _at(path, s):
    for a, b in zip(path, path[1:]):
        L = abs(b[0] - a[0]) + abs(b[1] - a[1])
        if s <= L + 1e-9:
            f = s / L if L > 0 else 0.0
            return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
        s -= L
    return path[-1]


def place_reps(fs, p, q, rep_um, step=2.16):
    """repeater points on the L route p -> q: n = ceil(L / rep_um) - 1 at equal arc length; an illegal one walks along
    the route to the nearest legal point (either direction, at most one stage); none legal on the route -> that
    repeater is dropped (a longer stage, which the stage model then prices)."""
    path = _lpath(p, q)
    L = abs(q[0] - p[0]) + abs(q[1] - p[1])
    n = max(0, int(math.ceil(L / rep_um - 1e-9)) - 1)
    out, bad = [], 0
    prev_s = 0.0
    for j in range(n):
        s0 = L * (j + 1) / (n + 1)
        best = None
        k = 0
        while k * step <= L / (n + 1):
            for s in ((s0,) if k == 0 else (s0 - k * step, s0 + k * step)):
                if prev_s < s < L and fs.legal(_at(path, s)):
                    best = s
                    break
            if best is not None:
                break
            k += 1
        if best is None:
            bad += 1
            continue
        prev_s = best
        out.append(_at(path, best))
    return out, bad


def leg_ps(fs, p, q, rep_um, Lin, corner="TT"):
    """delay from the input of the buffer at p to the input of the buffer at q (exact placed stages)."""
    reps, _ = place_reps(fs, p, q, rep_um)
    pts = [p] + reps + [q]
    d, li = 0.0, Lin
    for a, b in zip(pts, pts[1:]):
        L = abs(b[0] - a[0]) + abs(b[1] - a[1])
        d += stage_ps(L, li, corner)
        li = L
    return d, (abs(pts[-1][0] - pts[-2][0]) + abs(pts[-1][1] - pts[-2][1]))


def _sub(fs, q, kids, taps, rep_um, corner, Lin=250.0):
    """(lo, hi, first-stage lengths) of the subtree below a buffer at q: kids = [(xy, lo, hi)], taps = [(x, y)]."""
    lo, hi = math.inf, -math.inf
    tot = sum(abs(t[0] - q[0]) + abs(t[1] - q[1]) for t in taps)
    for t in taps:                       # leaf star: one stage, shared load
        L = abs(t[0] - q[0]) + abs(t[1] - q[1])
        s = STAGE_1X[corner]
        d = (s["d0"] + s["k1"] * tot + s["k2"] * L * L + s["ks"] * Lin) * SPICE_SCALE[corner]
        lo, hi = min(lo, d), max(hi, d)
    for xy, klo, khi in kids:
        d, _ = leg_ps(fs, q, xy, rep_um, Lin, corner)
        lo, hi = min(lo, d + klo), max(hi, d + khi)
    return lo, hi


def _sibling_match(fs, nodes, i, q, rep_um, corner, reach, n_grid, tol_ps):
    """the merge at q cannot be balanced by its own site (e.g. two kids on either side of a hard core: one leg is an
    unrepeatable stage): re-site each FAST movable kid (its own kids stay) so its arrival meets the slow kid's - a
    longer, legally-sited leg (GRT routes it as placed; no snake).  Accepted only if the node spread drops.
    -> new (lo, hi) of node i or None."""
    nd = nodes[i]

    def arr(k, xy):
        m = nodes[k]
        kk = [((nodes[c]["x"], nodes[c]["y"]), *nodes[c]["dme"]) for c in m["kids"]]
        a, b = _sub(fs, xy, kk, [tuple(t[2:4]) for t in m["taps"]], rep_um, corner)
        d, _ = leg_ps(fs, q, xy, rep_um, 250.0, corner)
        return d + a, d + b, a, b
    cur = {k: arr(k, (nodes[k]["x"], nodes[k]["y"])) for k in nd["kids"]}
    taps = [tuple(t[2:4]) for t in nd["taps"]]
    if taps:
        return None
    T = max(v[1] for v in cur.values())
    before = T - min(v[0] for v in cur.values())
    changed = {}
    for k in sorted(nd["kids"], key=lambda k: cur[k][1]):
        m = nodes[k]
        if m.get("fixed") or T - cur[k][1] <= tol_ps:
            continue
        c0 = (m["x"], m["y"])
        R = reach
        g = 2 * R / (2 * n_grid)
        best, bq = abs(T - cur[k][1]) + (cur[k][1] - cur[k][0]), None
        for a in range(2 * n_grid + 1):
            for b in range(2 * n_grid + 1):
                p = (round(c0[0] - R + a * g, 3), round(c0[1] - R + b * g, 3))
                if not (0 < p[0] < fs.W and 0 < p[1] < fs.H and fs.legal(p)):
                    continue
                lo, hi, *_ = arr(k, p)
                e = abs(T - hi) + (hi - lo) + max(0.0, hi - T) * 2
                if e < best - 1e-9:
                    best, bq = e, p
        if bq is not None:
            changed[k] = (c0, m.get("dme"))
            m["x"], m["y"] = bq
            _, _, a2, b2 = arr(k, bq)
            m["dme"] = (a2, b2)
            cur[k] = arr(k, bq)
    if not changed:
        return None
    lo, hi = min(v[0] for v in cur.values()), max(v[1] for v in cur.values())
    if hi - lo >= before - 1e-9:                    # no gain: undo
        for k, (c0, dm) in changed.items():
            nodes[k]["x"], nodes[k]["y"] = c0
            nodes[k]["dme"] = dm
        return None
    return lo, hi


def legal_dme(nodes, site, rep_um, corner="TT", reach=650.0, n_grid=15, keep=12, tol_ps=4.0, w_lat=0.02,
              only=None, column_slide=True, sibling_match=True, sib_tol_ps=15.0):
    """re-place every movable node (not fixed) bottom-up on the legal site minimising its subtree delay spread
    (exact stages, see module doc); -> stats dict.  nodes: die_trial node dict (x, y, parent, kids, taps, fixed,
    req_xy).  column_slide: a branching node of the plan's spine column (spine == 'column', all kids on the same
    column x) moves ALONG the column between its kids (vertical DME on the reserved, fully legal column; the strip
    leg rows below it stay).  only = optional set of node ids to process (one region).  Each node's subtree (lo, hi) is stored in
    nd['dme'] for reports."""
    fs = site if isinstance(site, FastSite) else FastSite(site)
    order, seen = [], set()
    roots = [i for i, nd in nodes.items() if nd["parent"] is None or nd["parent"] not in nodes]

    def post(i):                         # iterative post-order
        st = [(i, False)]
        while st:
            j, done = st.pop()
            if done:
                order.append(j)
                continue
            st.append((j, True))
            for k in nodes[j]["kids"]:
                st.append((k, False))
    for r in roots:
        post(r)
    alpha = stage_ps(rep_um, rep_um, corner) / rep_um          # ps/um of a regular repeated line (pre-filter)
    moved, gain, col_moves, sib = 0, [], [], []
    for i in order:
        nd = nodes[i]
        if only is not None and i not in only:
            continue
        taps = [tuple(t[2:4]) for t in nd["taps"]]
        kids = [((nodes[k]["x"], nodes[k]["y"]), *nodes[k]["dme"]) for k in nd["kids"]]
        cur = (nd["x"], nd["y"])
        lo, hi = _sub(fs, cur, kids, taps, rep_um, corner)
        col = (column_slide and nd.get("spine") == "column" and nd["parent"] is not None and len(kids) >= 2
               and all(abs(k[0][0] - cur[0]) < 1e-6 for k in kids) and not taps)
        if col:     # a branching node on the plan's legal spine column: DME along the column, between its kids
            ya, yb = min(k[0][1] for k in kids), max(k[0][1] for k in kids)
            best_q, best = cur, None
            for j in range(int((yb - ya) / 2.16) + 1):
                q = (cur[0], round(ya + j * 2.16, 3))
                if not fs.legal(q):
                    continue
                a, b = _sub(fs, q, kids, taps, rep_um, corner)
                e = (max(b - a, tol_ps) + w_lat * b, a, b)
                if best is None or e[0] < best[0] - 1e-9:
                    best_q, best = q, e
            if best is not None:
                if best_q != cur:
                    moved += 1
                    col_moves.append(round(abs(best_q[1] - cur[1]), 1))
                    gain.append((hi - lo) - (best[2] - best[1]))
                nd["x"], nd["y"] = best_q
                nd["dme"] = (best[1], best[2])
                continue
        if nd.get("fixed") or nd["parent"] is None or (not kids and len(taps) <= 1):
            nd["dme"] = (lo, hi)
            continue
        base = (hi - lo, hi)
        ideal = tuple(nd.get("req_xy") or cur)
        pts = [k[0] for k in kids] + list(taps)
        span = max(abs(a[0] - ideal[0]) + abs(a[1] - ideal[1]) for a in pts) if pts else 0.0
        R = min(reach, max(60.0, 0.75 * span))
        g = 2 * R / n_grid
        cands = {cur}
        if fs.legal(ideal):
            cands.add(ideal)
        for a in range(n_grid + 1):
            for b in range(n_grid + 1):
                q = (round(ideal[0] - R + a * g, 3), round(ideal[1] - R + b * g, 3))
                if 0 < q[0] < fs.W and 0 < q[1] < fs.H and fs.legal(q):
                    cands.add(q)

        def lin(q):
            ar = [alpha * (abs(k[0][0] - q[0]) + abs(k[0][1] - q[1])) for k in kids]
            v = [(a + k[1], a + k[2]) for a, k in zip(ar, kids)]
            v += [(stage_ps(abs(t[0] - q[0]) + abs(t[1] - q[1]), 250.0, corner),) * 2 for t in taps]
            mx, mn = max(x[1] for x in v), min(x[0] for x in v)
            return (max(mx - mn, tol_ps) + w_lat * mx)

        short = sorted(cands, key=lin)[:keep]

        def exact(q):
            a, b = _sub(fs, q, kids, taps, rep_um, corner)
            return (max(b - a, tol_ps) + w_lat * b, a, b)
        best_q, best = cur, exact(cur)
        for q in short:
            e = exact(q)
            if e[0] < best[0] - 1e-9:
                best_q, best = q, e
        for _ in range(2):               # local refine around the winner
            g2 = max(g / 4, 1.08)
            for a in (-2, -1, 0, 1, 2):
                for b in (-2, -1, 0, 1, 2):
                    q = (round(best_q[0] + a * g2, 3), round(best_q[1] + b * g2, 3))
                    if (a or b) and 0 < q[0] < fs.W and 0 < q[1] < fs.H and fs.legal(q):
                        e = exact(q)
                        if e[0] < best[0] - 1e-9:
                            best_q, best = q, e
        if best_q != cur:
            moved += 1
            gain.append(base[0] - (best[2] - best[1]))
        nd["x"], nd["y"] = best_q
        nd["dme"] = (best[1], best[2])
        if sibling_match and len(nd["kids"]) >= 2 and best[2] - best[1] > sib_tol_ps:
            r = _sibling_match(fs, nodes, i, best_q, rep_um, corner, reach, n_grid, tol_ps)
            if r is not None:
                sib.append(round((best[2] - best[1]) - (r[1] - r[0]), 1))
                nd["dme"] = r
    return dict(sibling_matched=len(sib), sibling_gain_ps_max=max(sib, default=0.0),nodes=len(order) if only is None else len(only), moved=moved, column_moves=len(col_moves),
                column_move_um_max=max(col_moves, default=0.0),
                spread_gain_ps_max=round(max(gain, default=0.0), 1),
                spread_gain_ps_sum=round(sum(gain), 1))
