"""Analytic die clock tree: geometric H-tree over the sink set, legal-site repeaters, insertion / skew prediction.

Construction (plan time, no placement/routing tool):
  * the frame box (die, or the sinks' bounding box) is bisected along its longer side, H-tree style, down to boxes
    no larger than leaf_um (full depth: every leaf is the same number of levels from the root -> equal tree length);
    empty boxes are pruned; tree node = box centre, slid to the nearest legal site (street or declared island)
    within max_move_um, else UNPLACED;
  * every leg (parent node -> child node; L path, x first, y first as the alternative) gets repeaters greedily
    at <= rep_um spacing, only on legal sites within lateral_um of the path.  A gap between legal sites longer
    than leg_max_um is a BLOCKED LEG (the plan-level form of 'clock span exceeds 480 um');
  * a leaf drives its sinks (macro clock pins / partition entries) with a repeated local leg;
  * delays: per driven segment d(L) (model.seg_ps), +branch_extra at a node that drives two kids.
Outputs per sink: tree arrival at the pin (TT/FF), stage count, chain of cells (for CPPR/LCA), latency = arrival +
the sink's own internal insertion.
"""
import math


class Tree:
    def __init__(self):
        self.cells = []        # dict(id, kind, xy, parent, level, arr{c}, depth)
        self.legs = []         # dict(parent, child, len_um, segs[], blocked[], route, ok)
        self.sinks = []        # dict(sink fields + leaf, arr{c}, stages, chain_top_cell)
        self.unplaced = []

    def add(self, kind, xy, parent, level, **kw):
        c = dict(id=len(self.cells), kind=kind, xy=tuple(xy), parent=parent, level=level, **kw)
        self.cells.append(c)
        return c["id"]

    def chain(self, cid):
        out = []
        while cid is not None:
            out.append(cid)
            cid = self.cells[cid]["parent"]
        return out


def _l_path(a, b, xfirst=True):
    m = (b[0], a[1]) if xfirst else (a[0], b[1])
    return [a, m, b]


def _poly_point(pts, s):
    for p, q in zip(pts, pts[1:]):
        L = abs(q[0] - p[0]) + abs(q[1] - p[1])
        if s <= L + 1e-9:
            t = 0 if L == 0 else s / L
            return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t), (abs(q[0] - p[0]) < 1e-9)
        s -= L
    return pts[-1], True


def place_leg(streets, a, b, cfg):
    """greedy repeaters on an L path a->b.  -> dict(len_um, segs[um], reps[xy], blocked[(s0, s1, span)], route)."""
    best = None
    for xfirst in (True, False):
        pts = _l_path(a, b, xfirst)
        L = abs(b[0] - a[0]) + abs(b[1] - a[1])
        step = cfg["step_um"]
        n = max(1, int(math.ceil(L / step)))
        samp = []
        for k in range(n + 1):
            s = min(L, k * step)
            p, vert = _poly_point(pts, s)
            ok = (k == 0 or k == n)          # endpoints: the node / pin itself
            q = p
            if not ok:
                for dl in cfg["lateral_offsets"]:
                    q = (p[0] + dl, p[1]) if vert else (p[0], p[1] + dl)
                    if streets is None or streets.legal(*q):
                        ok = True
                        break
            samp.append((s, ok, q if ok else p))
        rep, cut, pos, blocked = cfg["rep_um"], [0.0], 0.0, []
        reps = []
        i = 0
        while L - pos > rep + 1e-6:
            # farthest legal sample within rep of pos; else within leg_max; else blocked
            cand = [x for x in samp if pos + 1e-6 < x[0] <= pos + rep + 1e-6 and x[1]]
            if not cand:
                cand = [x for x in samp if pos + 1e-6 < x[0] <= pos + cfg["leg_max_um"] + 1e-6 and x[1]]
            if not cand:
                nxt = next((x for x in samp if x[0] > pos + 1e-6 and x[1]), samp[-1])
                blocked.append((round(pos, 2), round(nxt[0], 2), round(nxt[0] - pos, 2)))
                pos = nxt[0]
                cut.append(pos)
                if pos < L - 1e-6:
                    reps.append(nxt[2])
                continue
            x = cand[-1]
            pos = x[0]
            cut.append(pos)
            reps.append(x[2])
            i += 1
            if i > 10000:
                break
        if cut[-1] < L - 1e-6:
            cut.append(L)
        segs = [round(q - p, 3) for p, q in zip(cut, cut[1:])] or [0.0]
        r = dict(len_um=round(L, 2), segs=segs, reps=reps, blocked=blocked, route="x_first" if xfirst else "y_first")
        if best is None or len(r["blocked"]) < len(best["blocked"]) or (
                len(r["blocked"]) == len(best["blocked"]) and len(r["segs"]) < len(best["segs"])):
            best = r
        if not best["blocked"]:
            break
    return best


def build(sinks, W, H, model, streets=None, entry=None, cfg=None):
    """sinks: plan.clock_sinks() rows.  entry: clock source xy (None = die centre).  -> Tree"""
    cfg = dict(dict(leaf_um=None, leaf_sinks=1, max_move_um=None, step_um=None, frame="die", corners=("TT", "FF"),
                    lateral_um=None), **(cfg or {}))
    g = model["raster_um"]
    cfg["leaf_um"] = cfg["leaf_um"] or 2 * model["rep_um"] / 3
    cfg["max_move_um"] = cfg["max_move_um"] if cfg["max_move_um"] is not None else model["rep_um"] / 4
    cfg["step_um"] = cfg["step_um"] or g
    lat = cfg["lateral_um"] if cfg["lateral_um"] is not None else 2 * g
    k = int(lat // g)
    cfg["lateral_offsets"] = [0.0] + [s * i * g for i in range(1, k + 1) for s in (1, -1)]
    cfg["rep_um"], cfg["leg_max_um"] = model["rep_um"], model["leg_max_um"]
    corners = cfg["corners"]
    T = Tree()
    T.cfg = cfg
    if cfg["frame"] == "sinks" and sinks:
        xs, ys = [s["xy"][0] for s in sinks], [s["xy"][1] for s in sinks]
        box0 = (min(xs), min(ys), max(xs), max(ys))
    else:
        box0 = (0.0, 0.0, W, H)
    src = tuple(entry) if entry else ((box0[0] + box0[2]) / 2, (box0[1] + box0[3]) / 2)
    root = T.add("root", src, None, -1, arr={c: 0.0 for c in corners}, depth=0)

    def site(p, name):
        if streets is None:
            return p, 0.0
        r = streets.nearest_site(p[0], p[1], cfg["max_move_um"])
        if r is None:
            T.unplaced.append(dict(name=name, ideal=[round(p[0], 2), round(p[1], 2)],
                                   macro=(streets.macro_at(*p) or [None] * 5)[4]))
            return p, None
        return r

    def leg(pid, child_xy, child_kind, level, nkids_parent, name, extra=None):
        par = T.cells[pid]
        r = place_leg(streets, par["xy"], child_xy, cfg)
        arr = {}
        for c in corners:
            d = sum(model.seg_ps(s, c) for s in r["segs"])
            if nkids_parent > 1:
                d += model["branch_extra_ps"][c]
            arr[c] = par["arr"][c] + d
        prev = pid
        # repeaters are cells in the chain (count as stages for OCV)
        for q in r["reps"]:
            prev = T.add("rep", q, prev, level, arr=None, depth=T.cells[prev]["depth"] + 1)
        cid = T.add(child_kind, child_xy, prev, level, arr=arr, depth=T.cells[prev]["depth"] + 1, name=name, **(extra or {}))
        T.legs.append(dict(parent=pid, child=cid, name=name, level=level, len_um=r["len_um"], segs=r["segs"],
                           n_reps=len(r["reps"]), reps=r["reps"], blocked=r["blocked"], route=r["route"]))
        return cid

    def rec(box, members, pid, level, nkids_parent, tag):
        x0, y0, x1, y1 = box
        if level > 0 and len(members) <= (cfg["leaf_sinks"] or 0):
            # a box holding <= leaf_sinks sinks gets no node of its own: the parent node drives the pins directly
            T.cells[pid]["kind"] = "leaf" if T.cells[pid]["kind"] == "node" else T.cells[pid]["kind"]
            for s in members:
                sid = leg(pid, s["xy"], "pin", level, nkids_parent, s["name"])
                T.sinks.append(dict(s, cell=sid, leaf=pid))
            return
        c = ((x0 + x1) / 2, (y0 + y1) / 2)
        q, mv = site(c, f"n{level}_{tag}")
        nid = leg(pid, q, "node", level, nkids_parent, f"n{level}_{tag}", dict(ideal=c, move_um=mv, box=box))
        if max(x1 - x0, y1 - y0) <= cfg["leaf_um"] + 1e-6 or len(members) <= (cfg["leaf_sinks"] or 0):
            T.cells[nid]["kind"] = "leaf"
            for s in members:
                sid = leg(nid, s["xy"], "pin", level + 1, len(members), s["name"])
                T.sinks.append(dict(s, cell=sid, leaf=nid))
            return
        if x1 - x0 >= y1 - y0:
            xm = (x0 + x1) / 2
            parts = [((x0, y0, xm, y1), [s for s in members if s["xy"][0] < xm]),
                     ((xm, y0, x1, y1), [s for s in members if s["xy"][0] >= xm])]
        else:
            ym = (y0 + y1) / 2
            parts = [((x0, y0, x1, ym), [s for s in members if s["xy"][1] < ym]),
                     ((x0, ym, x1, y1), [s for s in members if s["xy"][1] >= ym])]
        live = [(i, b, m) for i, (b, m) in enumerate(parts) if m]
        for i, b, m in live:
            rec(b, m, nid, level + 1, len(live), tag + str(i))

    # sinks outside the frame box are clamped into it for bisection only
    rec(box0, list(sinks), root, 0, 1, "h")
    # per-sink stages / arrivals
    for s in T.sinks:
        ch = T.chain(s["cell"])
        s["chain"] = ch
        s["stages"] = sum(1 for cid in ch[1:] if T.cells[cid]["kind"] != "root")  # driving cells above the pin
        s["arr"] = dict(T.cells[s["cell"]]["arr"])
        s["latency"] = {c: s["arr"][c] + float(s["insertion_ps"].get(c, 0.0)) for c in corners}
    # arrival of repeater cells (linear interpolation not needed: OCV uses LCA = node/leaf/root cells only)
    return T


def lca(T, a, b):
    """last common cell of two sinks' chains with an arrival (a tree node / leaf / root)."""
    sb = set(b["chain"])
    for cid in a["chain"]:
        if cid in sb and T.cells[cid]["arr"] is not None:
            return cid
    return a["chain"][-1]


def stages_below(T, s, cid):
    """driving cells strictly below the LCA cell on the sink's chain (chain[0] is the pin itself)."""
    return max(0, s["chain"].index(cid) - 1)


def summary(T, corners=("TT", "FF")):
    out = {}
    for c in corners:
        arr = [s["arr"][c] for s in T.sinks]
        lat = [s["latency"][c] for s in T.sinks]
        out[c] = dict(insertion_min_ps=round(min(arr), 1) if arr else None, insertion_max_ps=round(max(arr), 1) if arr else None,
                      latency_min_ps=round(min(lat), 1) if lat else None, latency_max_ps=round(max(lat), 1) if lat else None)
    legs = T.legs
    bl = [lg for lg in legs if lg["blocked"]]
    spans = [b[2] for lg in bl for b in lg["blocked"]]
    blocked_over = [lg for lg in bl if any(b[2] > T.cfg["leg_max_um"] for b in lg["blocked"])]
    return dict(cells=len(T.cells), nodes=sum(1 for x in T.cells if x["kind"] in ("node", "leaf")),
                leaves=sum(1 for x in T.cells if x["kind"] == "leaf"), repeaters=sum(1 for x in T.cells if x["kind"] == "rep"),
                levels=max((x["level"] for x in T.cells), default=0), wire_um=round(sum(lg["len_um"] for lg in legs), 1),
                sinks=len(T.sinks), legs=len(legs), blocked_legs=len(blocked_over),
                blocked_span_um=[round(min(spans), 1), round(max(spans), 1)] if spans else None,
                unplaced=len(T.unplaced), corners=out)
