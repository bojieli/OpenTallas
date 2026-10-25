#!/usr/bin/env python3
"""OWNER RESET RULE (BRIEFING "OWNER DECISIONS" 2026-10-24 #2, amended by DECISION 13): pipeline reset like data.  THE
reset tool of every die.

CURRENT MODE = reset.release "wavefront" (OWNER DECISION 13, 2026-10-24 21:31; supersedes "equal depth to every tap"):
  * region = the WHOLE die: ONE root 2-flop synchroniser (ot_dp_rsync_s<N> u_rst_root) in the root partition (the one at
    the die rst_n pin, or reset.root_part); its async input = die rst_n = the only reset false path.  Every partition of
    the root's TYPE carries the synchroniser as its entry (uniform per type; at the others it sees a synchronous input).
  * NEIGHBOUR WAVEFRONT: every soft partition registers its incoming reset (arst_n -> pin register u_rst_in, interior
    pin at the type's IN site) and re-drives registered outs rst_o_<k> (interior pins at face sites, one relay each) to
    its neighbours; inside the partition an equal-depth relay tree (hops <= relay_um) reaches every clock tap and every
    rst_o.  Pins are uniform per type (the union of the sites any instance uses); the die top only wires a parent's
    rst_o_<k> to a child's arst_n (die hop <= hop_um, M8/M9), no die-top relays, no per-instance variants.
  * wf_solve picks per type the IN site (face midpoints, corners, face sites; reset.in_sites overrides) and per partition
    the parent (Dijkstra on release cycles + local search; objective: every partition within hop, then the latest
    release).  Hard partitions are leaves (their reset tap = IN; reset.depth clocks to release, default 1).
  * PUBLISHED OFFSETS (`reset_tree.py offsets PLAN.json [--out J]`): per partition the release cycle = clocks after the
    die rst_n deasserts at which its taps (and rst_o) release: root N + K_root, child release(parent) + entry + K
    (entry 1, or N for the root's type).  test_reset_wavefront.py checks the table against a simulation of the
    generated die.  The static schedule starts with an explicit start broadcast after reset (decision 13c); only
    control state is reset (13d).

LEGACY MODE "pipelined" (decision 2 as first written; G0 warns it is superseded):

Rule: exactly ONE root 2-flop reset synchroniser per die REGION (its async input is the only reset false path / CDC).
From it the synchronised reset travels as a SYNCHRONOUS signal through relay flops every <= 405 um (the data reach
rule), with EQUAL depth to every clock tap, so every block releases on the same known cycle.  Local flops use the
delivered reset with normal timed recovery/removal (or as a sync reset).  Assertion is synchronous too (the clock runs
at boot).  No recovery waivers.

Plan switch: reset.release "pipelined" (plan level; "counted" = the legacy per-tap asynchronous synchronisers).
  reset.relay_um     relay reach (default 405).  Trees are PLANNED at relay_um - MARGIN_UM (legalisation slack) and
                     CHECKED at relay_um (planned here, placed in the kit's reset_tree.tcl report).
  reset.part_depth   the partition reset contract K: relay stages from the partition's reset entry stage to every
                     clock tap, the SAME for every type of the plan (default: the deepest type's own tree depth).  A
                     replicated type then has one kit whatever its die position; the die tree pads per instance.
  reset.regions      [{name, parts?, root_um?}]: die regions (default ONE region = the whole die).  `parts` = member
                     partitions (default: every partition not listed in another region); `root_um` = the region's
                     root synchroniser site in the die frame (default: the die rst_n pin at the clock spine root,
                     gen_phys.die_root_pins).

Partition (kit) structure, per type (gen_rtl for generated kits, kit_rsync for bound kits):
  entry stage at the arst_n pin: ot_dp_rrelay u_rst_in, a plain pin register -- arst_n is a SYNCHRONOUS input (the die
  reset tree's last relay drives it; timed under the kit IO budget like any data pin; NO synchroniser, NO false path)
  -> rst_root_n -> relay tree ot_dp_rrelay u_rrl_<k>: shortest-hop tree over the clock taps, intermediate relays on
     the x-then-y L path (pushed off hard cores / macros), pads at the taps, depth exactly K at every tap -> rst_n_t<i>.
  Leaf contents take the tap nearest the outline centre (rst_n = rst_n_t<c>); boundary flops / ft stations their
  nearest tap (gen_rtl rsel, reset_taps.tcl after FIRM placement).
  Release at every tap: 1 + K clocks after the arst_n pin.
  (Interim, kit_rsync on a plan that is NOT pipelined: entry "sync" = ot_dp_rsync_s<N> u_rst_root at the pin, i.e. a
  region per partition; the partition's own depth.  Not the die-region rule: use only until the plan switches.)

Die level (the die top RTL and `reset_tree.py die`): per region ONE root synchroniser ot_dp_rsync_s<N> at root_um
(async input = the die rst_n pin: the region's only reset false path), then a die relay tree over the member
partitions' arst_n pins (die frame, same builder, hops <= relay_um) with equal depth E.  Every tap of the region is
released N + E + 1 + K clocks after rst_n deasserts.  HOSTING (OPEN): the die has no std-cell rows of its own
(partitions abut), so the root synchroniser and the die relays must sit inside partitions; `reset_tree.py die`
reports, per partition instance and type, the die relays falling in its outline.  The die top RTL instantiates them
at die level (functional model; exact boot cycles for benches).

usage (any form takes --release wavefront|pipelined to price a plan that has not switched yet):
       reset_tree.py offsets PLAN.json [--out J]    -> wavefront: per-partition release cycles (compiler / benches)
       reset_tree.py type PLAN.json TYPE            -> the type's tree summary (entry, depth, relays, boot cycles)
       reset_tree.py die  PLAN.json [--out J]       -> die regions: root, die depth E, hosting per partition, boot cycles
       reset_tree.py all  PLAN.json                 -> every type (G0 rule check) + die summary
       reset_tree.py render PLAN.json TYPE [--png F] [--release pipelined]   -> review picture of the type's tree"""
import heapq
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema as S  # noqa: E402

REACH_UM = 405.0        # owner rule: relay flops every <= 405 um
MARGIN_UM = 25.0        # planning slack under the reach (row / site snapping, ff_put_near spiral, macro push-off)
CLEAR_UM = 4.32         # relay sites stay this far off hard cores / macro leaves (one std-cell row + halo)


class ResetError(Exception):
    pass


# ----------------------------------------------------------------------------------------------- plan settings
def pipelined(P):
    return P.reset.get("release") == "pipelined"


def relay_um(P):
    return float(P.reset.get("relay_um", REACH_UM))


def sync_stages(P, tn=None):
    t = P.types[tn] if tn else {}
    return int((t.get("reset", {}) or {}).get("sync_stages", P.reset.get("sync_stages", 2)))


def die_root_um(P):
    """the die rst_n pin (gen_phys.die_root_pins: at the clock spine root)."""
    import gen_phys
    for name, _L, x, y in gen_phys.die_root_pins(P):
        if name == "rst_n":
            return (x, y)
    return (P.W / 2, P.H / 2)


def regions(P):
    """[{name, parts, root_um}] covering every partition exactly once."""
    allp = list(P.parts)
    regs = P.reset.get("regions")
    if not regs:
        return [dict(name="die", parts=allp, root_um=die_root_um(P))]
    out, seen = [], set()
    for r in regs:
        seen |= set(r.get("parts") or [])
    rest = [n for n in allp if n not in seen]
    for r in regs:
        parts = list(r.get("parts") or rest)
        out.append(dict(name=r["name"], parts=parts, root_um=tuple(r.get("root_um") or die_root_um(P))))
    return out


# ----------------------------------------------------------------------------------------------- geometry
def _man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _hops(a, b, reach):
    return max(1, math.ceil(_man(a, b) / reach - 1e-9))


def _lpath(a, b, n):
    """n interior points at equal spacing on the x-then-y L path a -> b."""
    L = _man(a, b)
    dx = abs(b[0] - a[0])
    pts = []
    for j in range(1, n + 1):
        s = L * j / (n + 1)
        if s <= dx:
            pts.append((a[0] + math.copysign(s, b[0] - a[0]), a[1]))
        else:
            pts.append((b[0], a[1] + math.copysign(s - dx, b[1] - a[1])))
    return pts


def blockages(t, clear=CLEAR_UM):
    """hard cores and macro leaves (contents with a lef) of a type, grown by `clear`: [(x0, y0, x1, y1)]."""
    out = []
    for c in list(t.get("hard_cores", []) or []) + [c for c in t.get("contents", []) or [] if c.get("lef")]:
        if "origin_um" not in c or "outline_um" not in c:
            continue
        (ox, oy), (cw, ch) = c["origin_um"], c["outline_um"]
        if c.get("orient") in ("R90", "R270", "MXR90", "MYR90"):
            cw, ch = ch, cw
        out.append((ox - clear, oy - clear, ox + cw + clear, oy + ch + clear))
    return out


def _free(p, boxes, box_out):
    x, y = p
    x0, y0, x1, y1 = box_out
    if not (x0 <= x <= x1 and y0 <= y <= y1):
        return False
    return not any(a < x < c and b < y < d for a, b, c, d in boxes)


def push_off(p, boxes, box_out, step=2.16):
    """nearest point outside every blockage and inside box_out: candidates are the projections onto the faces of the
    boxes holding the point (repeated while a projection lands in another box), nearest free one wins."""
    if not boxes or _free(p, boxes, box_out):
        return p
    x0o, y0o, x1o, y1o = box_out

    def clampo(q):
        return (min(max(q[0], x0o), x1o), min(max(q[1], y0o), y1o))
    eps = 0.01
    seen, front, best = set(), [p], None
    for _ in range(6):
        nxt = []
        for q in front:
            for a, b, c, d in boxes:
                if not (a < q[0] < c and b < q[1] < d):
                    continue
                for r in ((a - eps, q[1]), (c + eps, q[1]), (q[0], b - eps), (q[0], d + eps)):
                    r = clampo((round(r[0], 4), round(r[1], 4)))
                    if r in seen:
                        continue
                    seen.add(r)
                    if _free(r, boxes, box_out):
                        dd = _man(p, r)
                        if best is None or (dd, r) < best:
                            best = (dd, r)
                    else:
                        nxt.append(r)
        if best is not None:
            return best[1]
        front = nxt
    # fully tiled blockages (no channel between abutting cores): nearest free point of an 8.64 um scan
    best = None
    st = 8.64
    nx, ny = int((x1o - x0o) / st) + 1, int((y1o - y0o) / st) + 1
    for j in range(ny):
        for i in range(nx):
            q = (x0o + i * st, y0o + j * st)
            dd = _man(p, q)
            if (best is None or dd < best[0]) and _free(q, boxes, box_out):
                best = (dd, q)
    return best[1] if best else p


# ----------------------------------------------------------------------------------------------- the tree
def build(taps, root_xy, depth=None, reach=REACH_UM, margin=MARGIN_UM, boxes=(), box_out=None, prefix=""):
    """taps [(name, x, y)] (tap index = list index); root_xy = the entry stage (reset pin).
    Topology: a shortest-hop tree over the taps (ties: fewer intermediate relays, then shorter wire) with intermediate
    relays on the x-then-y L path, pushed off `boxes`; when a push-off breaks the reach, a shortest-hop tree over a
    grid of free relay sites (wires may cross blockages, relays may not).  Equal depth: every tap is padded to D =
    max(own depth, `depth`); pads go as HIGH in the tree as possible (on the edge into the subtree that has slack), so
    one pad serves every tap below it.
    Returns {root, depth, own_depth, relays[{name, xy, d, q, depth, tap, kind}], reach_um, max_hop_um, ...}."""
    topo = topology(taps, root_xy, reach, margin, boxes, box_out)
    return assign(topo, depth, prefix)


def topology(taps, root_xy, reach=REACH_UM, margin=MARGIN_UM, boxes=(), box_out=None):
    """the depth-independent part of build(): relay sites and parents.  A tap (or the entry) over a blockage gets its
    relay site at the nearest free point (tap_offset_um records how far)."""
    if not taps:
        raise ResetError("reset tree: no taps")
    root = (float(root_xy[0]), float(root_xy[1]))
    pts = [(float(x), float(y)) for _, x, y in taps]
    off = 0.0
    if box_out is not None and boxes:
        root = push_off(root, boxes, box_out)
        sites = [push_off(p, boxes, box_out) for p in pts]
        off = max(_man(a, b) for a, b in zip(pts, sites))
        pts = sites
    plan_reach = reach - margin
    nodes, method = _topo_taps(pts, root, plan_reach, boxes, box_out), "taps"
    if _maxhop(nodes, root) > reach + 1e-6 and boxes:
        nodes, method = _topo_grid(pts, root, plan_reach, boxes, box_out), "grid"
    return dict(nodes=nodes, root=root, ntap=len(pts), reach=reach, plan_reach=plan_reach, method=method,
                taps=[n for n, _, _ in taps], tap_offset_um=round(off, 1))


def assign(topo, depth=None, prefix=""):
    T = _assign(topo["nodes"], topo["root"], topo["ntap"], depth, prefix)
    reach = topo["reach"]
    T.update(reach_um=reach, plan_reach_um=topo["plan_reach"], topology=topo["method"], taps=list(topo["taps"]),
             tap_offset_um=topo["tap_offset_um"])
    if T["max_hop_um"] > reach + 1e-6:
        raise ResetError(f"reset tree: max hop {T['max_hop_um']} um > {reach:g} um (no relay site within reach)")
    return T


def _maxhop(nodes, root):
    return max(_man(nodes[v]["xy"], root if nodes[v]["par"] < 0 else nodes[nodes[v]["par"]]["xy"])
               for v in range(len(nodes)))


def _topo_taps(pts, root, reach, boxes, box_out):
    """nodes [{xy, par (-1 = root), tap (index or None)}]: taps first (node i = tap i), then wire relays."""
    n = len(pts)
    dist = {-1: (0, 0, 0.0)}
    par = {}
    pq = [(0, 0, 0.0, -1)]
    done = set()
    while pq:
        h, nw, w, u = heapq.heappop(pq)
        if u in done:
            continue
        done.add(u)
        pu = root if u < 0 else pts[u]
        for v in range(n):
            if v in done:
                continue
            e = _hops(pu, pts[v], reach)
            c = (h + e, nw + e - 1, w + _man(pu, pts[v]))
            if v not in dist or c < dist[v]:
                dist[v] = c
                par[v] = u
                heapq.heappush(pq, c + (v,))
    nodes = [dict(xy=pts[v], par=None, tap=v) for v in range(n)]
    for v in sorted(range(n), key=lambda v: dist[v]):
        u = par[v]
        pu = root if u < 0 else pts[u]
        prev = u
        for p in _lpath(pu, pts[v], _hops(pu, pts[v], reach) - 1):
            if box_out is not None:
                p = push_off(p, boxes, box_out)
            nodes.append(dict(xy=p, par=prev, tap=None))
            prev = len(nodes) - 1
        nodes[v]["par"] = prev
    return nodes


def _topo_grid(pts, root, reach, boxes, box_out, pitch=None):
    """shortest-hop tree over the taps + a grid of free relay sites (pitch um); ties: fewer hops, then less wire."""
    x0, y0, x1, y1 = box_out
    pitch = pitch or max(21.6, reach / 4)
    while (x1 - x0) * (y1 - y0) / pitch ** 2 > 3000:
        pitch *= 1.5
    grid = []
    nx, ny = int((x1 - x0) / pitch) + 1, int((y1 - y0) / pitch) + 1
    for j in range(ny):
        for i in range(nx):
            q = (x0 + i * pitch, y0 + j * pitch)
            if _free(q, boxes, box_out):
                grid.append(q)
    # thin channels between abutting blockages / along the outline: sites ON every blockage edge (the blockages are
    # grown by CLEAR_UM, so an edge point is CLEAR_UM off the core; two cores 2 x CLEAR_UM apart share that line)
    eps = 0.0
    for a, b, c, d in list(boxes) + [(x0 - 2 * eps, y0 - 2 * eps, x1 + 2 * eps, y1 + 2 * eps)]:
        for t in range(int(max(c - a, d - b) / pitch) + 2):
            for q in ((min(a + t * pitch, c), b - eps), (min(a + t * pitch, c), d + eps),
                      (a - eps, min(b + t * pitch, d)), (c + eps, min(b + t * pitch, d))):
                if box_out is not None and not (x0 <= q[0] <= x1 and y0 <= q[1] <= y1):
                    q = (min(max(q[0], x0), x1), min(max(q[1], y0), y1))
                if _free(q, boxes, box_out):
                    grid.append(q)
    grid = sorted(set(grid))
    allp = list(pts) + grid               # node index: taps first
    cell = reach
    buckets = {}
    for k, q in enumerate(allp):
        buckets.setdefault((int(q[0] // cell), int(q[1] // cell)), []).append(k)

    def near(q):
        cx, cy = int(q[0] // cell), int(q[1] // cell)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for k in buckets.get((cx + dx, cy + dy), ()):
                    if _man(q, allp[k]) <= reach:
                        yield k
    dist = {}
    par = {}
    pq = [(0, 0.0, -1)]
    best = {-1: (0, 0.0)}
    while pq:
        h, w, u = heapq.heappop(pq)
        if u in dist:
            continue
        dist[u] = (h, w)
        pu = root if u < 0 else allp[u]
        for v in near(pu):
            if v in dist:
                continue
            c = (h + 1, w + _man(pu, allp[v]))
            if v not in best or c < best[v]:
                best[v] = c
                par[v] = u
                heapq.heappush(pq, c + (v,))
    miss = [v for v in range(len(pts)) if v not in dist]
    if miss:
        raise ResetError(f"reset tree: taps {miss[:5]} unreachable through free relay sites within {reach:g} um")
    nodes = [dict(xy=pts[v], par=None, tap=v) for v in range(len(pts))]
    gid = {}
    for v in range(len(pts)):
        chain, u = [], par[v]
        while u >= 0 and u >= len(pts) and u not in gid:
            chain.append(u)
            u = par[u]
        top = u if u < len(pts) else gid[u]            # a tap (or -1) or an already-made grid node
        for g in reversed(chain):
            nodes.append(dict(xy=allp[g], par=top, tap=None))
            gid[g] = top = len(nodes) - 1
        u = par[v]
        nodes[v]["par"] = u if u < len(pts) else gid[u]
    return nodes


def _assign(nodes, root, ntap, depth, prefix):
    """relay names / nets / depths with shared pads: D = max(structural depth, depth)."""
    kids = {}
    for v, nd in enumerate(nodes):
        kids.setdefault(nd["par"], []).append(v)
    order, st = [], [-1]
    while st:                                  # preorder from the root
        u = st.pop()
        if u >= 0:
            order.append(u)
        st += sorted(kids.get(u, []), reverse=True)
    sdep = {-1: 0}
    for v in order:
        sdep[v] = sdep[nodes[v]["par"]] + 1
    H = {}
    for v in reversed(order):                  # remaining structural relays below v to its deepest tap
        H[v] = max([1 + H[c] for c in kids.get(v, [])] + [0])
    own = max(sdep[v] for v in range(ntap))
    D = max(own, int(depth or 0))
    relays, net, k, arr = [], {-1: f"{prefix}rst_root_n"}, 0, {-1: 0}
    tap_own_net = {}

    def add(xy, d, kind, tap, dep, last_tap=None):
        nonlocal k
        q = f"{prefix}rst_n_t{last_tap}" if last_tap is not None else f"{prefix}rst_rl_{k}"
        relays.append(dict(name=f"{prefix}u_rrl_{k}", xy=xy, d=d, q=q, depth=dep, tap=tap, kind=kind))
        k += 1
        return q
    for v in order:
        nd = nodes[v]
        u = nd["par"]
        src, a = net[u], arr[u]
        slack = D - (a + 1) - H[v]
        tapv = nd["tap"]
        for _ in range(slack):                 # shared pads on the edge into v's subtree (at v's site)
            a += 1
            src = add(nd["xy"], src, "pad", tapv, a)
        a += 1
        leaf_done = tapv is not None and a == D
        q = add(nd["xy"], src, "tap" if tapv is not None else "wire", tapv, a, tapv if leaf_done else None)
        net[v], arr[v] = q, a
        if tapv is not None and not leaf_done:    # an interior tap: its own output padded to D at the tap
            s2 = q
            for j in range(a + 1, D + 1):
                s2 = add(nd["xy"], s2, "pad", tapv, j, tapv if j == D else None)
            tap_own_net[tapv] = s2
    xy = {r["q"]: r["xy"] for r in relays}
    xy[f"{prefix}rst_root_n"] = root
    maxhop = max(_man(xy[r["d"]], r["xy"]) for r in relays)
    return dict(root=root, depth=D, own_depth=own, relays=relays, max_hop_um=round(maxhop, 1),
                tap_depth={v: sdep[v] for v in range(ntap)},
                n_tree=sum(r["kind"] != "pad" for r in relays), n_pad=sum(r["kind"] == "pad" for r in relays))


def verify(T):
    """structural rule check of a built tree: [errors]."""
    errs = []
    drv = {T["relays"][0]["d"]} if T["relays"] else set()
    qs = {}
    for r in T["relays"]:
        if r["q"] in qs:
            errs.append(f"net {r['q']} driven twice")
        qs[r["q"]] = r
    root_net = next((r["d"] for r in T["relays"] if r["d"].endswith("rst_root_n")), None)
    for r in T["relays"]:
        if r["d"] != root_net and r["d"] not in qs:
            errs.append(f"{r['name']}: input {r['d']} has no driver")
    # depth along the driver chain, equal at every tap
    def dep(net):
        n = 0
        while net != root_net:
            net = qs[net]["d"]
            n += 1
        return n
    taps = list(range(len(T["taps"])))
    for v in taps:
        net = next((r["q"] for r in T["relays"] if r["q"].endswith(f"rst_n_t{v}")), None)
        if net is None:
            errs.append(f"tap {v}: no rst_n_t{v}")
        elif dep(net) != T["depth"]:
            errs.append(f"tap {v}: depth {dep(net)} != {T['depth']}")
    del drv
    if T["max_hop_um"] > T["reach_um"] + 1e-6:
        errs.append(f"max hop {T['max_hop_um']} > {T['reach_um']}")
    return errs


# ----------------------------------------------------------------------------------------------- per type
_TAPS = {}


def _taps(P, tn):
    """schema.tap_grid memoised per Plan instance (tap_clear on a fully tiled core array costs ~40 s per call); the entry
    holds P, so the id cannot be reused while cached."""
    e = _TAPS.get((id(P), tn))
    if e is None or e[0] is not P:
        e = _TAPS[(id(P), tn)] = (P, _S_TAP_GRID(P, tn))
    return list(e[1])


_S_TAP_GRID = S.tap_grid


def reset_pin(P, tn):
    """gen_phys.tap_points(P, tn)[1] (the arst_n tap, type frame) with the memoised tap grid."""
    import gen_phys
    S.tap_grid = _taps
    try:
        return tuple(gen_phys.tap_points(P, tn)[1])
    finally:
        S.tap_grid = _S_TAP_GRID


def _type_tree(P, tn, depth, reach):
    import copy
    cache = P.__dict__.setdefault("_reset_tree_cache", {})
    key = (tn, depth, reach)
    if key not in cache:
        cache[key] = _type_tree0(P, tn, depth, reach)
    return copy.deepcopy(cache[key])


def _type_tree0(P, tn, depth, reach):
    cache = P.__dict__.setdefault("_reset_tree_cache", {})
    if ("topo", tn, reach) not in cache:
        t = P.types[tn]
        w, h = t["outline_um"]
        cache[("topo", tn, reach)] = topology(_taps(P, tn), reset_pin(P, tn), reach=reach,
                                              boxes=blockages(t), box_out=(CLEAR_UM, CLEAR_UM, w - CLEAR_UM,
                                                                           h - CLEAR_UM))
    return assign(cache[("topo", tn, reach)], depth)


def part_depth(P):
    """the plan's partition reset contract K (reset.part_depth, else the deepest non-hard type's own tree depth)."""
    if P.reset.get("part_depth") is not None:
        return int(P.reset["part_depth"])
    cache = P.__dict__.setdefault("_reset_tree_cache", {})
    if "K" not in cache:
        reach = relay_um(P)
        cache["K"] = max([_type_tree(P, tn, None, reach)["own_depth"] for tn, t in P.types.items()
                          if not t.get("hard")] or [1])
    return cache["K"]


def for_type(P, tn, reach=None):
    """the reset tree of a plan type in its own frame (taps = schema.tap_grid, entry = gen_phys reset tap).
    Pipelined plans: entry 'relayed', depth = the plan contract K.  Other plans (kit_rsync interim): entry 'sync', the
    type's own depth."""
    reach = float(reach or relay_um(P))
    if wavefront(P):
        if P.types[tn].get("hard"):
            raise ResetError(f"type {tn}: hard partitions carry no generated reset tree")
        T = _wf_type_tree(P, tn)
        T.update(entry="sync" if tn == wf_solve(P)["root_type"] else "relayed", sync_stages=sync_stages(P, tn),
                 type=tn)
        return T
    if pipelined(P):
        K = part_depth(P)
        T = _type_tree(P, tn, K, reach)
        if T["own_depth"] > K:
            raise ResetError(f"type {tn}: own reset tree depth {T['own_depth']} > the plan contract "
                             f"reset.part_depth {K}")
        ent = "relayed"
    else:
        ent = "sync"
        T = _type_tree(P, tn, None, reach)
    T.update(entry=ent, sync_stages=sync_stages(P, tn), type=tn)
    return T


def entry_stages(T):
    return T["sync_stages"] if T["entry"] == "sync" else 1


def release_clocks(T):
    """clocks from the entry pin (arst_n deassert for 'sync', the synchronous reset edge for 'relayed') to the release
    of every tap."""
    return entry_stages(T) + T["depth"]


# ----------------------------------------------------------------------------------------------- die level


def part_reset_pin(P, n):
    """a partition's arst_n pin in the die frame (hard partitions: their reset tap, else their centre)."""
    try:
        return P.to_die(n, reset_pin(P, P.parts[n]["type"]))
    except Exception:
        x0, y0, x1, y1 = P.rect(n)
        return ((x0 + x1) / 2, (y0 + y1) / 2)


def die_plan(P):
    """per region: ONE root synchroniser at root_um, then the die relay tree to every member partition's arst_n pin
    (die frame; equal depth E; hosting = the partition whose outline holds each die relay / the root)."""
    cache = P.__dict__.setdefault("_reset_tree_cache", {})
    if "die" in cache:
        return cache["die"]
    reach = relay_um(P)
    rects = {n: P.rect(n) for n in P.parts}

    def host(x, y):
        return next((n for n, (x0, y0, x1, y1) in rects.items() if x0 <= x <= x1 and y0 <= y <= y1), "(none)")
    regs = []
    for i, r in enumerate(regions(P)):
        pins = [(n,) + tuple(part_reset_pin(P, n)) for n in r["parts"]]
        T = build(pins, r["root_um"], reach=reach, box_out=(0, 0, P.W, P.H), prefix=f"die{i}_")
        hosts = {}
        for rl in T["relays"]:
            hosts.setdefault(host(*rl["xy"]), []).append(rl["name"])
        regs.append(dict(name=r["name"], index=i, root_um=[round(v, 3) for v in r["root_um"]],
                         root_host=host(*r["root_um"]), members=len(pins), die_depth=T["depth"],
                         relays=len(T["relays"]), tree_relays=T["n_tree"], pad_relays=T["n_pad"],
                         max_hop_um=T["max_hop_um"], hosts={k: len(v) for k, v in hosts.items()},
                         part_of_tap={j: n for j, (n, _, _) in enumerate(pins)}, tree=T))
    out = dict(regions=regs)
    cache["die"] = out
    return out


def die_summary(P):
    if wavefront(P):
        W = wf_plan(P)
        return {k: v for k, v in W.items() if k != "parts"}
    K = part_depth(P)
    N = sync_stages(P)
    rows = []
    for r in die_plan(P)["regions"]:
        hosts = r["hosts"]
        per_type = {}
        for n in P.parts:
            per_type.setdefault(P.parts[n]["type"], []).append(hosts.get(n, 0))
        nonuni = sorted(tn for tn, cs in per_type.items() if len(set(cs)) > 1)
        hp = sorted(((c, n) for n, c in hosts.items() if n in P.parts), reverse=True)
        rows.append(dict(region=r["name"], root_um=r["root_um"], root_host=r["root_host"], members=r["members"],
                         die_depth_E=r["die_depth"], die_relays=r["relays"], die_tree_relays=r["tree_relays"],
                         die_pad_relays=r["pad_relays"], max_hop_um=r["max_hop_um"],
                         release_clocks=N + r["die_depth"] + 1 + K,
                         boot_cycles_added_vs_one_sync=r["die_depth"] + 1 + K,
                         host_partitions=len(hp), unhosted=hosts.get("(none)", 0),
                         max_relays_in_one_partition=hp[0][0] if hp else 0, busiest_hosts=hp[:5],
                         types_with_nonuniform_hosting=len(nonuni), nonuniform_types=nonuni[:20]))
    return dict(release="pipelined" if pipelined(P) else P.reset.get("release", "counted"), sync_stages=N,
                part_depth_K=K, relay_um=relay_um(P), regions=rows)


def die_rtl(P, ind="    "):
    """die top lines: per region the root synchroniser + die relay tree; returns (lines, {part: net})."""
    N = sync_stages(P)
    lines, net = [], {}
    for r in die_plan(P)["regions"]:
        T, i = r["tree"], r["index"]
        lines.append(f"{ind}// OWNER RESET RULE 10-24 region {r['name']}: ONE root synchroniser + die relay tree, depth "
                     f"{T['depth']} to {r['members']} partition reset pins (hops <= {T['reach_um']:g} um); HOSTING OPEN: "
                     "these cells sit inside partitions (reset_tree.py die)")
        lines.append(f"{ind}wire die{i}_rst_root_n;")
        lines.append(f"{ind}ot_dp_rsync_s{N} die{i}_u_rst_root (.clk(clk), .async_rst_n(rst_n), "
                     f".sync_rst_n(die{i}_rst_root_n));  // @ {r['root_um']} in {r['root_host']}")
        for rl in T["relays"]:
            lines.append(f"{ind}wire {rl['q']};")
            lines.append(f"{ind}ot_dp_rrelay {rl['name']} (.clk(clk), .d({rl['d']}), .q({rl['q']}));  "
                         f"// {rl['kind']} depth {rl['depth']} @ ({rl['xy'][0]:.0f}, {rl['xy'][1]:.0f})")
        for j, n in r["part_of_tap"].items():
            net[n] = f"die{i}_rst_n_t{j}"
    return lines, net


# ----------------------------------------------------------------------------------------------- WAVEFRONT (decision 13)
INSET_UM = 8.64         # reset in / out interior pins sit this far inside the partition face
HARD_DEPTH = 1          # a hard partition (prebuilt) without reset.depth: its pin register only


def wavefront(P):
    return P.reset.get("release") == "wavefront"


def delivered(P):
    """the partition takes arst_n as a SYNCHRONOUS input (pipelined or wavefront plan)."""
    return pipelined(P) or wavefront(P)


def hop_um(P):
    """die-level reset hop reach: parent rst_o relay -> child u_rst_in (default reset.relay_um)."""
    return float(P.reset.get("hop_um", relay_um(P)))


def _snap(P, x, y):
    import gen_phys
    return tuple(gen_phys._snap_tap(P, x, y))


def face_sites(P, tn):
    """candidate reset pin sites of a soft type (type frame): along every face, INSET_UM inside, spaced so that every
    point of the face is within (hop - margin) / 2 of one; pushed off hard cores / macro leaves and off the clock tap
    pins; snapped like the tap pins.  [{face, j, mid, xy}]"""
    cache = P.__dict__.setdefault("_reset_tree_cache", {})
    key = ("sites", tn)
    if key in cache:
        return cache[key]
    t = P.types[tn]
    w, h = t["outline_um"]
    sp = max(50.0, hop_um(P) - MARGIN_UM)
    boxes = blockages(t)
    box_out = (CLEAR_UM, CLEAR_UM, w - CLEAR_UM, h - CLEAR_UM)
    taken = [(x, y) for _, x, y in _taps(P, tn)]
    out = []
    for face, L in (("S", w), ("E", h), ("N", w), ("W", h)):
        m = max(1, math.ceil(L / sp))
        for j in range(m):
            s = (j + 0.5) * L / m
            x, y = {"S": (s, INSET_UM), "N": (s, h - INSET_UM), "W": (INSET_UM, s), "E": (w - INSET_UM, s)}[face]
            if boxes:
                x, y = push_off((x, y), boxes, box_out)
            x, y = _snap(P, x, y)
            for _ in range(8):           # never two pins on one spot (GRT-0080)
                if not any(abs(x - a) < 1.0 and abs(y - b) < 1.0 for a, b in taken):
                    break
                x, y = _snap(P, x + (8.64 if face in "SN" else 0.0), y + (8.64 if face in "EW" else 0.0))
            taken.append((x, y))
            out.append(dict(face=face, j=j, mid=(j == m // 2), xy=(x, y)))
    cache[key] = out
    return out


def corner_sites(P, tn):
    """the four corner IN-pin candidates of a soft type (INSET_UM inside both faces; reachable from two sides)."""
    cache = P.__dict__.setdefault("_reset_tree_cache", {})
    key = ("corners", tn)
    if key not in cache:
        t = P.types[tn]
        w, h = t["outline_um"]
        boxes = blockages(t)
        box_out = (CLEAR_UM, CLEAR_UM, w - CLEAR_UM, h - CLEAR_UM)
        taken = [(x, y) for _, x, y in _taps(P, tn)] + [s["xy"] for s in face_sites(P, tn)]
        out = []
        for x, y in ((INSET_UM, INSET_UM), (w - INSET_UM, INSET_UM), (w - INSET_UM, h - INSET_UM),
                     (INSET_UM, h - INSET_UM)):
            if boxes:
                x, y = push_off((x, y), boxes, box_out)
            x, y = _snap(P, x, y)
            if not any(abs(x - a) < 1.0 and abs(y - b) < 1.0 for a, b in taken):
                out.append((x, y))
                taken.append((x, y))
        cache[key] = out
    return cache[key]


def _est_depth(P, tn, xy):
    """planning estimate of a type's relay depth from an entry at xy (reach-limited hops to the farthest tap / site)."""
    pr = relay_um(P) - MARGIN_UM
    pts = [(x, y) for _, x, y in _taps(P, tn)] + [s["xy"] for s in face_sites(P, tn)]
    return max(1, max(math.ceil(_man(xy, p) / pr) for p in pts))


def _root_part(P, soft):
    rx, ry = die_root_um(P)

    def dist(n):
        x0, y0, x1, y1 = P.rect(n)
        return max(x0 - rx, 0, rx - x1) + max(y0 - ry, 0, ry - y1)
    return min(soft, key=lambda n: (dist(n), n))


def wf_solve(P):
    """die wavefront routing: per soft type the reset IN site (one of its four face-midpoint sites, or
    reset.in_sites[type]) and per partition its parent (the partition whose rst_o site is within hop of its IN pin and
    releases first).  Dijkstra on release cycles with estimated type depths; local search over the IN faces
    (objective: unreachable partitions, latest release, sum of releases)."""
    cache = P.__dict__.setdefault("_reset_tree_cache", {})
    if "wf_solve" in cache:
        return cache["wf_solve"]
    N = sync_stages(P)
    hp = hop_um(P) - MARGIN_UM
    hard = {n for n in P.parts if P.types[P.parts[n]["type"]].get("hard")}
    soft = sorted(n for n in P.parts if n not in hard)
    if not soft:
        raise ResetError("reset wavefront: no soft partition to carry the reset")
    root = P.reset.get("root_part") or _root_part(P, soft)
    stypes = sorted({P.parts[n]["type"] for n in soft})
    over = P.reset.get("in_sites") or {}
    cands = {}
    for tn in stypes:
        if tn in over:
            cands[tn] = [_snap(P, *over[tn])]
        else:          # face midpoints first (the initial choice prefers them), then corners, then every face site
            fs = face_sites(P, tn)
            cands[tn] = [s["xy"] for s in fs if s["mid"]] + corner_sites(P, tn) + \
                [s["xy"] for s in fs if not s["mid"]]
    est = {(tn, c): _est_depth(P, tn, c) for tn in stypes for c in cands[tn]}
    hdep = {n: int((P.types[P.parts[n]["type"]].get("reset") or {}).get("depth", HARD_DEPTH)) for n in hard}
    # every soft partition's out sites in the die frame, bucketed
    cell = max(hp, 1.0)
    grid = {}
    for q in soft:
        for j, s in enumerate(face_sites(P, P.parts[q]["type"])):
            X, Y = P.to_die(q, s["xy"])
            grid.setdefault((int(X // cell), int(Y // cell)), []).append((q, j, X, Y))

    def near(p, xy):
        X, Y = xy
        cx, cy = int(X // cell), int(Y // cell)
        out = []
        for i in (-1, 0, 1):
            for k in (-1, 0, 1):
                for q, j, x, y in grid.get((cx + i, cy + k), ()):
                    d = abs(x - X) + abs(y - Y)
                    if q != p and d <= hp + 1e-6:
                        out.append((q, j, round(d, 1)))
        return out
    ein = {}                                   # (p, cand) -> [(q, j, d)]
    for p in soft:
        for c in cands[P.parts[p]["type"]]:
            ein[(p, c)] = near(p, P.to_die(p, c))
    for p in hard:
        ein[(p, None)] = near(p, part_reset_pin(P, p))
    rtype = P.parts[root]["type"]

    def entry(p):
        return N if P.parts[p]["type"] == rtype else 1

    def solve(choice):
        adj = {}
        for p in soft:
            for q, j, d in ein[(p, choice[P.parts[p]["type"]])]:
                adj.setdefault(q, []).append((p, j, d))
        for p in hard:
            for q, j, d in ein[(p, None)]:
                adj.setdefault(q, []).append((p, j, d))
        rel = {root: N + est[(rtype, choice[rtype])]}
        par = {root: None}
        hq = [(rel[root], root)]
        done = set()
        while hq:
            r, q = heapq.heappop(hq)
            if q in done:
                continue
            done.add(q)
            for p, j, d in sorted(adj.get(q, ())):
                if p in hard:
                    rp = r + 1 + hdep[p] - 1
                else:
                    rp = r + entry(p) + est[(P.parts[p]["type"], choice[P.parts[p]["type"]])]
                if p not in rel or rp < rel[p]:
                    rel[p], par[p] = rp, (q, j, d)
                    heapq.heappush(hq, (rp, p))
        unr = sorted(n for n in P.parts if n not in rel)
        return (len(unr), max(rel.values()), sum(rel.values())), rel, par, unr

    def toward_root(tn):
        rx = P.to_die(root, (0, 0))
        inst = [n for n in soft if P.parts[n]["type"] == tn]
        return min(cands[tn], key=lambda c: (sum(_man(P.to_die(n, c), rx) for n in inst), c))
    choice = {tn: toward_root(tn) for tn in stypes}
    best = solve(choice)

    def descend(types, rounds):
        nonlocal choice, best
        for _round in range(rounds):
            improved = False
            for tn in types:
                for c in cands[tn]:
                    if c == choice[tn]:
                        continue
                    trial = dict(choice)
                    trial[tn] = c
                    r = solve(trial)
                    if r[0] < best[0]:
                        choice, best, improved = trial, r, True
            if not improved:
                break
    # (1) reach everything: the types of unreachable soft partitions and of their neighbours, until no gain
    for _ in range(6):
        if not best[3]:
            break
        before = best[0]
        bad = {P.parts[n]["type"] for n in best[3] if n not in hard}
        for n in best[3]:
            x0, y0, x1, y1 = P.rect(n)
            for q in soft:
                a0, b0, a1, b1 = P.rect(q)
                if a0 <= x1 + 1 and x0 <= a1 + 1 and b0 <= y1 + 1 and y0 <= b1 + 1:
                    bad.add(P.parts[q]["type"])
        descend(sorted(bad), 1)
        if best[0] == before:
            break
    # (2) shorten the wavefront: one pass over every type
    descend(stypes, 1)
    obj, rel, par, unr = best
    # partitions still unreachable within hop: attach to the nearest reached rst_o site (flagged: G0 error, the
    # owner of the plan moves the reset pin -- hard types: partition_types[T].reset.tap_um on a face)
    for p in sorted(unr):
        xy = part_reset_pin(P, p) if p in hard else P.to_die(p, choice[P.parts[p]["type"]])
        b = None
        for q in sorted(rel):
            if q in hard:
                continue
            for j, s_ in enumerate(face_sites(P, P.parts[q]["type"])):
                d = _man(P.to_die(q, s_["xy"]), xy)
                if b is None or d < b[0]:
                    b = (d, q, j)
        if b is not None:
            q = b[1]
            par[p] = (q, b[2], round(b[0], 1))
            rel[p] = rel[q] + (hdep[p] if p in hard else entry(p) + est[(P.parts[p]["type"],
                                                                          choice[P.parts[p]["type"]])])
    outs = {tn: set() for tn in stypes}
    for p, pr in par.items():
        if pr is not None:
            outs[P.parts[pr[0]]["type"]].add(pr[1])
    res = dict(root=root, root_type=rtype, choice=choice, parent=par, unreachable=unr, est_rel=rel,
               outs={tn: sorted(v) for tn, v in outs.items()}, hard=sorted(hard), hard_depth=hdep)
    cache["wf_solve"] = res
    return res


def in_pin(P, tn):
    """the wavefront reset IN pin (arst_n) of a soft type (type frame)."""
    return tuple(wf_solve(P)["choice"][tn])


def out_pins(P, tn):
    """[(port, x, y)] the registered reset outputs of a soft type (uniform per type: every site any instance uses)."""
    if not wavefront(P) or P.types[tn].get("hard"):
        return []
    sites = face_sites(P, tn)
    return [(f"rst_o_{k}",) + tuple(sites[j]["xy"]) for k, j in enumerate(wf_solve(P)["outs"].get(tn, []))]


def _wf_type_tree(P, tn):
    cache = P.__dict__.setdefault("_reset_tree_cache", {})
    key = ("wf_tree", tn)
    if key not in cache:
        t = P.types[tn]
        w, h = t["outline_um"]
        taps = _taps(P, tn)
        outs = out_pins(P, tn)
        pts = list(taps) + [(f"o{k}", x, y) for k, (_, x, y) in enumerate(outs)]
        topo = topology(pts, in_pin(P, tn), reach=relay_um(P), boxes=blockages(t),
                        box_out=(CLEAR_UM, CLEAR_UM, w - CLEAR_UM, h - CLEAR_UM))
        T = assign(topo, None)
        T.update(n_clock_taps=len(taps), outs=[[x, y] for _, x, y in outs])
        cache[key] = T
    import copy
    return copy.deepcopy(cache[key])


def wf_plan(P):
    """the published wavefront: per type (IN pin, outs, depth K, entry), per partition (parent, parent rst_o port,
    die hop, entry stages, release cycle = clocks after die rst_n deasserts at which its taps and rst_o release)."""
    cache = P.__dict__.setdefault("_reset_tree_cache", {})
    if "wf_plan" in cache:
        return cache["wf_plan"]
    sol = wf_solve(P)
    N = sync_stages(P)
    types = {}
    for tn in sorted({P.parts[n]["type"] for n in P.parts if n not in sol["hard"]}):
        T = for_type(P, tn)
        types[tn] = dict(in_um=[round(v, 4) for v in in_pin(P, tn)], outs=[[o[0], round(o[1], 4), round(o[2], 4)]
                         for o in out_pins(P, tn)], depth_K=T["depth"], entry=T["entry"],
                         entry_stages=entry_stages(T), release_after_pin=release_clocks(T), relays=len(T["relays"]),
                         max_hop_um=T["max_hop_um"])
    kids = {}
    for p, pr in sol["parent"].items():
        if pr is not None:
            kids.setdefault(pr[0], []).append(p)
    parts, st = {}, [sol["root"]]
    while st:
        p = st.pop()
        pr = sol["parent"][p]
        tn = P.parts[p]["type"]
        base = 0 if pr is None else parts[pr[0]]["release"]
        if p in sol["hard"]:
            rel = base + sol["hard_depth"][p]
            ent, K = 1, sol["hard_depth"][p] - 1
        else:
            rel = base + types[tn]["release_after_pin"]
            ent, K = types[tn]["entry_stages"], types[tn]["depth_K"]
        row = dict(type=tn, parent=None if pr is None else pr[0], entry_stages=ent, depth_K=K, release=rel)
        if pr is None:
            row.update(source="die rst_n (asynchronous: the ONE root synchroniser)")
        else:
            q = pr[0]
            k = sol["outs"][P.parts[q]["type"]].index(pr[1])
            row.update(source=f"{q}.rst_o_{k}", hop_um=pr[2])
        parts[p] = row
        st += sorted(kids.get(p, []))
    out = dict(release="wavefront", sync_stages=N, root=sol["root"], root_type=sol["root_type"],
               hop_um=hop_um(P), relay_um=relay_um(P), unreachable=sol["unreachable"],
               max_release=max([r["release"] for r in parts.values()] or [0]),
               max_die_hop_um=max([r.get("hop_um", 0.0) for r in parts.values()] or [0.0]),
               long_hops=sorted([[p, r["source"], r["hop_um"]] for p, r in parts.items()
                                 if r.get("hop_um", 0.0) > hop_um(P) + 1e-6], key=lambda x: -x[2]),
               types=types, parts=dict(sorted(parts.items())),
               note="OWNER DECISION 13 (2026-10-24): one root 2-flop synchroniser; neighbour wavefront; release = "
                    "clocks after die rst_n deasserts at which the partition's taps (and its rst_o) release; the "
                    "static schedule starts with an explicit start broadcast after reset")
    cache["wf_plan"] = out
    return out


def wf_die_rtl(P, ind="    "):
    """die top: the root partition's arst_n = rst_n (die pin); every other arst_n = its parent's rst_o_<k>.
    Returns (wire lines, {part: arst_n net}, {part: {port: net}})."""
    W = wf_plan(P)
    lines = [f"{ind}// OWNER DECISION 13 reset wavefront: root {W['root']} (ONE root synchroniser on rst_n); every "
             f"partition re-drives a registered reset to its neighbours; latest release {W['max_release']} clocks"]
    arst, outs = {}, {}
    for p, r in W["parts"].items():
        if r["parent"] is None:
            arst[p] = "rst_n"
        else:
            net = "rstw_" + re.sub(r"\W", "_", r["source"])
            if net not in {n for d in outs.values() for n in d.values()}:
                lines.append(f"{ind}wire {net};")
            outs.setdefault(r["parent"], {})[r["source"].split(".")[-1]] = net
            arst[p] = net
    return lines, arst, outs


# ----------------------------------------------------------------------------------------------- RTL / TCL
def relay_sv():
    """the ot_dp_rrelay module text (held in gen_rtl.CELLS, the one copy of the kit cells)."""
    import gen_rtl
    return re.search(r"(//[^\n]*ot_dp_rrelay.*?\nendmodule\n)", gen_rtl.CELLS, re.S).group(1)


def rtl_lines(T, ind="    ", src="arst_n"):
    """SystemVerilog body lines: entry stage + relays.  Declares rst_n_t<i> for every tap."""
    ns = T["sync_stages"]
    if T["entry"] == "sync" and ns not in (2, 3):
        raise ResetError(f"reset_tree: sync_stages {ns} (root synchronisers exist for 2 or 3)")
    taps = list(range(len(T["taps"])))
    out = [f"{ind}// OWNER RESET RULE 10-24 (tools/die_plan/reset_tree.py): entry {T['entry']} + synchronous relay tree, "
           f"depth {T['depth']} to all {len(taps)} taps, hops <= {T['reach_um']:g} um; release {release_clocks(T)} "
           f"clocks after the entry pin",
           f"{ind}wire rst_root_n;"]
    if T["entry"] == "sync":
        out.append(f"{ind}ot_dp_rsync_s{ns} u_rst_root (.clk(clk), .async_rst_n({src}), .sync_rst_n(rst_root_n));  "
                   "// the region's ONE root synchroniser: its async input is the only reset false path")
    else:
        out.append(f"{ind}ot_dp_rrelay u_rst_in (.clk(clk), .d({src}), .q(rst_root_n));  "
                   "// pin register of the SYNCHRONOUS reset input (die reset tree)")
    out += [f"{ind}wire rst_n_t{i};" for i in taps]
    for r in T["relays"]:
        if not r["q"].startswith("rst_n_t"):
            out.append(f"{ind}wire {r['q']};")
        out.append(f"{ind}ot_dp_rrelay {r['name']} (.clk(clk), .d({r['d']}), .q({r['q']}));  "
                   f"// {r['kind']} tap {r['tap']} depth {r['depth']} @ ({r['xy'][0]:.1f}, {r['xy'][1]:.1f})")
    nck = T.get("n_clock_taps", len(taps))
    for k in range(len(T.get("outs", []))):
        out.append(f"{ind}assign rst_o_{k} = rst_n_t{nck + k};  // registered reset out (wavefront): the relay at "
                   f"({T['outs'][k][0]:.1f}, {T['outs'][k][1]:.1f}), released with the taps")
    return out


def leaf_tap(P, tn):
    """the tap whose relay drives the leaf contents' rst_n: nearest the outline centre (halves the leaf reset reach
    vs tap 0 in the SW corner)."""
    w, h = P.types[tn]["outline_um"]
    taps = _taps(P, tn)
    return min(range(len(taps)), key=lambda i: (abs(taps[i][1] - w / 2) + abs(taps[i][2] - h / 2), i))


TCL_HEAD = """# GENERATED by tools/die_plan/reset_tree.py (OWNER RESET RULE 10-24): FIRM sites of the reset entry stage (root
# synchroniser u_rst_root or synchronous pin register u_rst_in, at the arst_n pin) and of the synchronous reset relays
# u_rrl_<k> (hops <= REACH).  Sourced inside face_flops.tcl (PRE_GLOBAL_PLACE) before reset_taps.tcl; uses its
# ff_put_near / ff_blk / ff_dbu.  Listed in ot_face_flops.txt so face_flops_release.tcl hands them to DPL.
set rtr_n 0; set rtr_miss {}; set rtr_at {}
set rtr_fh [open $::env(RESULTS_DIR)/ot_face_flops.txt a]
proc rtr_place {key pat x y tag} {
  global ff_blk ff_dbu rtr_n rtr_miss rtr_fh rtr_at
  set hit 0
  foreach i [$ff_blk getInsts] {
    set nm [$i getName]
    if {![string match $pat $nm]} continue
    if {![string match "*DFF*" [[$i getMaster] getName]]} continue
    set got [ff_put_near $i [expr {round($x * $ff_dbu)}] [expr {round($y * $ff_dbu)}]]
    if {$got eq ""} { lappend rtr_miss $nm; continue }
    puts $rtr_fh "$nm\\t$tag\\t[expr {[lindex $got 0] / double($ff_dbu)}]\\t[expr {[lindex $got 1] / double($ff_dbu)}]\\t-"
    dict set rtr_at $key $got
    incr rtr_n; incr hit
  }
  if {!$hit} { lappend rtr_miss $pat }
}
"""


def tcl_text(T):
    ent = "u_rst_root" if T["entry"] == "sync" else "u_rst_in"
    t = [TCL_HEAD.replace("REACH", f"{T['reach_um']:g} um"),
         f"rtr_place rst_root_n {{*{ent}[./]*}} {T['root'][0]:.3f} {T['root'][1]:.3f} rentry"]
    for r in T["relays"]:
        t.append(f"rtr_place {r['q']} {{*{r['name']}[./]*}} {r['xy'][0]:.3f} {r['xy'][1]:.3f} rrl:{r['kind']}{r['depth']}")
    edges = " ".join(f"{r['q']} {r['d']}" for r in T["relays"])
    t += ["close $rtr_fh",
          "# placed hop check (driver relay -> relay, Manhattan between placed sites)",
          f"set rtr_hmax 0; set rtr_hbad 0; set rtr_lim [expr {{{T['reach_um']:g} * $ff_dbu}}]",
          f"foreach {{q d}} {{{edges}}} {{",
          "  if {![dict exists $rtr_at $q] || ![dict exists $rtr_at $d]} continue",
          "  lassign [dict get $rtr_at $q] x1 y1; lassign [dict get $rtr_at $d] x0 y0",
          "  set h [expr {abs($x1 - $x0) + abs($y1 - $y0)}]",
          "  if {$h > $rtr_hmax} { set rtr_hmax $h }",
          "  if {$h > $rtr_lim} { incr rtr_hbad }",
          "}",
          "set rtr_v [expr {($rtr_hbad || [llength $rtr_miss]) ? \"FAIL\" : \"PASS\"}]",
          f"puts \"OT_RESET_TREE entry {T['entry']} depth {T['depth']} ({T['n_tree']} tree + {T['n_pad']} pad relays, "
          f"planned max hop {T['max_hop_um']} um): placed $rtr_n flops FIRM, placed max hop "
          "[format %.1f [expr {$rtr_hmax / double($ff_dbu)}]] um, $rtr_hbad hops > "
          f"{T['reach_um']:g} um: $rtr_v (missing: [llength $rtr_miss] $rtr_miss)\""]
    return "\n".join(t) + "\n"


def summary(T):
    return dict(entry=T["entry"], depth=T["depth"], own_depth=T["own_depth"], relays=len(T["relays"]),
                tree_relays=T["n_tree"], pad_relays=T["n_pad"], max_hop_um=T["max_hop_um"], reach_um=T["reach_um"],
                root_um=[round(v, 3) for v in T["root"]], sync_stages=T["sync_stages"],
                entry_stages=entry_stages(T), release_clocks=release_clocks(T), outs=len(T.get("outs", [])),
                note="OWNER DECISION 13: one root synchroniser per die + neighbour wavefront (registered reset in / out "
                     "per partition, relays <= reach, equal depth inside the partition)" if T.get("outs") is not None
                else "OWNER RESET RULE 10-24: one root synchroniser per die region + equal-depth synchronous relays")


# ----------------------------------------------------------------------------------------------- G0
def check(P):
    """(errors, warnings, info) of the reset rule for a plan (check.py G0)."""
    errs, warns = [], []
    if wavefront(P):
        try:
            for tn, t in sorted(P.types.items()):
                if t.get("hard") or not any(p["type"] == tn for p in P.parts.values()):
                    continue
                T = for_type(P, tn)
                errs += [f"type {tn}: reset tree: {e}" for e in verify(T)]
            W = wf_plan(P)
            if W["long_hops"] or W["unreachable"]:
                errs.append(f"reset wavefront: {len(W['long_hops'])} partitions have no neighbour rst_o within "
                            f"{hop_um(P):g} um of their reset IN pin (attached to the nearest, hop um): "
                            f"{[(a, c) for a, _b, c in W['long_hops'][:12]]}; move the IN pin (hard types: "
                            "partition_types[T].reset.tap_um on the face toward a neighbour) or the floorplan")
            info = {k: v for k, v in W.items() if k not in ("parts",)}
        except ResetError as e:
            errs.append(str(e))
            info = None
        return errs, warns, info
    if pipelined(P):
        warns.append("reset.release 'pipelined' (equal depth through a die relay tree) is superseded by OWNER DECISION "
                     "13 (2026-10-24): use 'wavefront'")
    if not pipelined(P):
        warns.append("reset.release is not 'wavefront': per-partition asynchronous synchronisers do not meet the OWNER "
                     "RESET RULE 2026-10-24 / DECISION 13 (tools/die_plan/reset_tree.py)")
        return errs, warns, None
    try:
        K = part_depth(P)
        for tn, t in sorted(P.types.items()):
            if t.get("hard"):
                continue
            T = for_type(P, tn)
            errs += [f"type {tn}: reset tree: {e}" for e in verify(T)]
        info = die_summary(P)
        for r in info["regions"]:
            if r["max_hop_um"] > relay_um(P) + 1e-6:
                errs.append(f"region {r['region']}: die reset hop {r['max_hop_um']} um > {relay_um(P):g}")
        info["part_depth_K"] = K
    except ResetError as e:
        errs.append(str(e))
        info = None
    return errs, warns, info


def render(P, tn, png):
    """review picture of a type's reset tree (review-before-route): outline, hard cores / macro leaves, clock taps, the
    arst_n entry, relays coloured by depth, driver -> relay edges (straight lines; the wire takes an L)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    T = for_type(P, tn)
    t = P.types[tn]
    w, h = t["outline_um"]
    fig, ax = plt.subplots(figsize=(8, 8 * h / max(w, 1e-9) if w else 8))
    ax.add_patch(Rectangle((0, 0), w, h, fill=False, lw=1.5, ec="k"))
    for a, b, c, d in blockages(t):
        ax.add_patch(Rectangle((a, b), c - a, d - b, fc="#ddd", ec="#999", lw=0.5))
    xy = {r["q"]: r["xy"] for r in T["relays"]}
    xy["rst_root_n"] = T["root"]
    cm = plt.get_cmap("viridis")
    for r in T["relays"]:
        (x0, y0), (x1, y1) = xy[r["d"]], r["xy"]
        ax.plot([x0, x1], [y0, y1], "-", color="#c33" if RT_hop(x0, y0, x1, y1) > T["reach_um"] else "#888", lw=0.6)
    for r in T["relays"]:
        ax.plot(*r["xy"], "o", ms=3 if r["kind"] == "pad" else 5, color=cm(r["depth"] / max(1, T["depth"])))
    for i, (_, x, y) in enumerate(_taps(P, tn)):
        ax.plot(x, y, "+", color="b", ms=7)
    ax.plot(*T["root"], "s", color="r", ms=9)
    ax.set_title(f"{tn}: reset entry {T['entry']} (red square) -> depth {T['depth']} to {len(T['taps'])} taps (+), "
                 f"{T['n_tree']} tree + {T['n_pad']} pad relays, max hop {T['max_hop_um']} um", fontsize=8)
    ax.set_xlim(-0.02 * w, 1.02 * w)
    ax.set_ylim(-0.02 * h, 1.02 * h)
    ax.set_aspect("equal")
    fig.savefig(png, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return png


def RT_hop(x0, y0, x1, y1):
    return abs(x1 - x0) + abs(y1 - y0)


def main(argv):
    if len(argv) >= 3 and argv[0] == "render":
        P = S.Plan(json.load(open(argv[1])), argv[1])
        if "--release" in argv:
            P.reset["release"] = argv[argv.index("--release") + 1]
        out = argv[argv.index("--png") + 1] if "--png" in argv else f"reset_tree_{argv[2]}.png"
        print(render(P, argv[2], out))
        return 0
    if len(argv) < 2 or argv[0] not in ("type", "die", "all", "offsets"):
        raise SystemExit(__doc__)
    P = S.Plan(json.load(open(argv[1])), argv[1])
    if "--release" in argv:             # what-if: price a plan that has not switched yet
        P.reset["release"] = argv[argv.index("--release") + 1]
    if argv[0] == "type":
        print(json.dumps(dict(type=argv[2], **summary(for_type(P, argv[2])))))
    elif argv[0] == "offsets":
        if not wavefront(P):
            raise SystemExit("offsets: the plan is not reset.release 'wavefront' (add --release wavefront to price it)")
        js = json.dumps(wf_plan(P), indent=1)
        if "--out" in argv:
            Path(argv[argv.index("--out") + 1]).write_text(js + "\n")
        print(js)
    elif argv[0] == "die":
        s = die_summary(P)
        js = json.dumps(s, indent=1)
        if "--out" in argv:
            Path(argv[argv.index("--out") + 1]).write_text(js + "\n")
        print(js)
    else:
        e, w, info = check(P)
        print(json.dumps(dict(errors=e, warnings=w, die=info), indent=1))
        return 1 if e else 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
