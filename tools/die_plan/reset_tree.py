#!/usr/bin/env python3
"""OWNER RESET RULE (BRIEFING "OWNER DECISIONS" 2026-10-24 #2): pipeline reset like data.  THE reset tool of every die.

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

usage: reset_tree.py type PLAN.json TYPE            -> the type's tree summary (entry, depth, relays, boot cycles)
       reset_tree.py die  PLAN.json [--out J]       -> die regions: root, die depth E, hosting per partition, boot cycles
       reset_tree.py all  PLAN.json                 -> every type (G0 rule check) + die summary"""
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


def _topo_grid(pts, root, reach, boxes, box_out, pitch=21.6):
    """shortest-hop tree over the taps + a grid of free relay sites (pitch um); ties: fewer hops, then less wire."""
    x0, y0, x1, y1 = box_out
    while (x1 - x0) * (y1 - y0) / pitch ** 2 > 3000:
        pitch *= 1.5
    grid = []
    nx, ny = int((x1 - x0) / pitch) + 1, int((y1 - y0) / pitch) + 1
    for j in range(ny):
        for i in range(nx):
            q = (x0 + i * pitch, y0 + j * pitch)
            if _free(q, boxes, box_out):
                grid.append(q)
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


def _type_tree(P, tn, depth, reach):
    import copy
    cache = P.__dict__.setdefault("_reset_tree_cache", {})
    key = (tn, depth, reach)
    if key not in cache:
        cache[key] = _type_tree0(P, tn, depth, reach)
    return copy.deepcopy(cache[key])


def _type_tree0(P, tn, depth, reach):
    import gen_phys
    cache = P.__dict__.setdefault("_reset_tree_cache", {})
    if ("topo", tn, reach) not in cache:
        t = P.types[tn]
        w, h = t["outline_um"]
        cache[("topo", tn, reach)] = topology(S.tap_grid(P, tn), gen_phys.tap_points(P, tn)[1], reach=reach,
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
    import gen_phys
    try:
        return P.to_die(n, gen_phys.tap_points(P, P.parts[n]["type"])[1])
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
    return out


def leaf_tap(P, tn):
    """the tap whose relay drives the leaf contents' rst_n: nearest the outline centre (halves the leaf reset reach
    vs tap 0 in the SW corner)."""
    w, h = P.types[tn]["outline_um"]
    taps = S.tap_grid(P, tn)
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
          "set rtr_v [expr {$rtr_hbad ? \"FAIL\" : \"PASS\"}]",
          f"puts \"OT_RESET_TREE entry {T['entry']} depth {T['depth']} ({T['n_tree']} tree + {T['n_pad']} pad relays, "
          f"planned max hop {T['max_hop_um']} um): placed $rtr_n flops FIRM, placed max hop "
          "[format %.1f [expr {$rtr_hmax / double($ff_dbu)}]] um, $rtr_hbad hops > "
          f"{T['reach_um']:g} um: $rtr_v (missing: [llength $rtr_miss] $rtr_miss)\""]
    return "\n".join(t) + "\n"


def summary(T):
    return dict(entry=T["entry"], depth=T["depth"], own_depth=T["own_depth"], relays=len(T["relays"]),
                tree_relays=T["n_tree"], pad_relays=T["n_pad"], max_hop_um=T["max_hop_um"], reach_um=T["reach_um"],
                root_um=[round(v, 3) for v in T["root"]], sync_stages=T["sync_stages"],
                entry_stages=entry_stages(T), release_clocks=release_clocks(T),
                note="OWNER RESET RULE 10-24: one root synchroniser per die region + equal-depth synchronous relays")


# ----------------------------------------------------------------------------------------------- G0
def check(P):
    """(errors, warnings, info) of the reset rule for a plan (check.py G0)."""
    errs, warns = [], []
    if not pipelined(P):
        warns.append("reset.release is not 'pipelined': per-partition asynchronous synchronisers do not meet the OWNER "
                     "RESET RULE 2026-10-24 (tools/die_plan/reset_tree.py)")
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


def main(argv):
    if len(argv) < 2 or argv[0] not in ("type", "die", "all"):
        raise SystemExit(__doc__)
    P = S.Plan(json.load(open(argv[1])), argv[1])
    if argv[0] == "type":
        print(json.dumps(dict(type=argv[2], **summary(for_type(P, argv[2])))))
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
