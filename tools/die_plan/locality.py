#!/usr/bin/env python3
"""LOCALITY-SCORE-1: traffic matrix, locality score, region proposer and the 12.14b one-page ESTIMATE (METHODOLOGY
12.13 a/b/c/e, 12.14b).  Analysis only: no plan, RTL, kit or calendar edit.

    locality.py score   --plan PLAN --regions MAP --die NAME --v-ps-mm V --out DIR [--tag T] [--feed fwd|top]
    locality.py propose --plan PLAN --die NAME --v-ps-mm V --out DIR [--span-mm 3.5] [--regions BASE_MAP]
    MAP = a JSON file with {"part_region": {part: region}} (fallback_regions / hbm_land_regions format) or a flat
          {part: region} dict, or the word 'part' (every partition its own region).

(1) TRAFFIC.  Every plan port src.part -> dst.part (both real partitions) carries `width` bits over the Manhattan
    distance of the two partition centres: bit-mm = width x d / 1000.  The matrix is undirected (a, b sorted).
(2) SCORE of a region map: bits / bit-mm inside vs across regions, crossing ports and region pairs, FAR crossings
    (region pairs that do not touch: 12.13c says they become hop chains through the regions between), and per crossing
    the ESTIMATED unshared clock and derated crossing margin of the clock feed (below).
(3) PROPOSE: connectivity clustering (greedy merge of the heaviest-traffic cluster pair) under a span cap (bounding box
    max side <= --span-mm; no foreign partition centre inside the merged box); a hard partition first joins its port
    neighbours (it cannot host a landing ring, as fallback_regions.merge_hard).  Feed = neighbour-forwarded graph along
    the links (below).
(4) RENDER: PNG of partitions coloured by region, region boxes, the feed graph and the crossings coloured by margin.
(5) ESTIMATE: one markdown page per die (delay/mm x span x derate, crossing margins, tracks demand vs supply).

CLOCK FEED MODEL (estimate; every region tree is an equal-length tree from its bounding-box centre):
  I_r          = v x (w_r + h_r) / 2                      region insertion (centre -> farthest corner, Manhattan)
  feed 'fwd'   = maximum-weight spanning tree of the region adjacency graph (weight = crossing bits), rooted at the
                 region of least eccentricity.  Child c is fed from a LEAF of its parent p at the tap t (bit-weighted
                 mean of the p<->c crossing points): T_root(c) = T_root(p) + I_p + v x |t - centre(c)|_1 (+ pad_c).
  feed 'top'   = one balanced H-tree from the die-graph centre to every region root (the die-wide form of 12.13f):
                 a virtual TOP region over the box of the region centres, its leaves at the roots, each region
                 delayed by I_max - I_r so every leaf of the die arrives together (nominal d = 0).
  feed 'spt'   = shortest-path tree of the same adjacency graph (forward delay I_p + v |t - centre(c)|_1), least
                 eccentricity root: the shallowest neighbour-forwarded feed.
  Entry of a crossing in region R = a leaf: arrival T_root(R) + I_R.  Two leaves p, q of ONE region tree part at the
  H-tree node whose box is first cut between them (recursive bisection of the longer side): they diverge
  v x (w_k + h_k) / 2 above the leaves (w_k, h_k = that node's box; the full I when the root cut separates them).  For a crossing
  A <-> B the last common point is in L = the lowest common feed ancestor of A and B, between the two points of L that
  lead to A and B (the crossing point itself if A or B == L, else the tap toward the child on the path).
  unshared(A) = arrival(entry A) - arrival(last common point); class-A stages = unshared / mu_stage(A); the 12.3 core
  latency (250 TT / 202.5 FF) is added as class B on both sides, exactly as landed_phase_ocv.
  FF delays = TT x mu_stage(A,FF) / mu_stage(A,TT) (ASSUMED scaling of the measured TT trunk delay/mm).
MARGIN: the shared model, by calling tools/s81_head/landed_phase_ocv.analyse (LAND-HEAD-2, reused, not forked) on a
  synthetic tree with these branches: clk_aocv g021 (random A/B, 0.21 %/mm on the bounding-box diagonal of the two
  entries + the common point, nets +-3 %), droop 'regions' (+5.11 % one-sided late: different regions).
  Three readings of the nominal d (one common whole-cycle count k per crossing for TT and FF, chosen at the TT/FF mean):
   RAW   margin = P/2 - max(|d + p_up|, |d - p_dn|)          (today's ring, unfolded d)
   FOLD  the same with d - kP                               (count-aligned crossing, MESO-COUNT verdict pending)
   PAD   whole-cycle-padded forwarded hops: each forwarded child gets the TT pad that puts its leaves on a whole cycle
         of its parent's leaves; the pad is clock delay (class A) and joins the unshared branch; d - kP at TT and FF.
  The gate is 12.13d (landed_phase_ocv >= 100 ps TT and FF on every crossing, measured after GRT); these are PREDICTIONS.
TRACKS: the bits of each region pair route along the region adjacency graph (shortest centre path); demand per touching
  boundary = bits crossing it, supply = budgets.face_pins_per_um x shared face length (pins on the partition faces).
"""
import argparse
import collections
import gzip
import heapq
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools" / "s81_head"))
import clk_aocv as CA  # noqa: E402
import landed_phase_ocv as LP  # noqa: E402

TABLE = HERE / "clk_aocv_table_g021.json"
CORE_LAT = {"TT": 250.0, "FF": 202.5}
ADJ_TOL_UM = 60.0


# ----------------------------------------------------------------------------------------------------- plan / traffic
def load_plan(plan):
    P = json.loads(Path(plan).read_text()) if not isinstance(plan, dict) else plan
    T = P["partition_types"]
    parts = {}
    for p in P["partitions"]:
        t = T[p["type"]]
        w, h = t["outline_um"]
        x, y = p["origin_um"]
        parts[p["name"]] = dict(rect=(x, y, x + w, y + h), cen=(x + w / 2, y + h / 2), area=w * h,
                                hard=bool(t.get("hard")))
    ports = [dict(id=q["id"], src=q["src"]["part"], dst=q["dst"]["part"], width=int(q.get("width", 1)),
                  kind=q.get("kind", "data"))
             for q in P["ports"] if q["src"]["part"] in parts and q["dst"]["part"] in parts
             and q["src"]["part"] != q["dst"]["part"]]
    die = P["die"]
    return dict(parts=parts, ports=ports, outline=die["outline_um"], period=float(die.get("period_ps", 833.0)),
                face_pins_per_um=float(P.get("budgets", {}).get("face_pins_per_um", 6.0)))


def manh(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def traffic(D):
    """undirected partition traffic matrix {(a, b): {bits, bitmm, ports}} with a < b."""
    M = collections.defaultdict(lambda: dict(bits=0, bitmm=0.0, ports=0))
    for q in D["ports"]:
        a, b = sorted((q["src"], q["dst"]))
        m = M[(a, b)]
        m["bits"] += q["width"]
        m["bitmm"] += q["width"] * manh(D["parts"][a]["cen"], D["parts"][b]["cen"]) / 1000.0
        m["ports"] += 1
    return dict(M)


def load_regions(spec, D):
    if spec == "part":
        return {n: n for n in D["parts"]}
    r = json.loads(Path(spec).read_text()) if not isinstance(spec, dict) else spec
    r = r.get("part_region", r)
    miss = sorted(set(D["parts"]) - set(r))
    if miss:
        raise SystemExit(f"region map lacks {len(miss)} partitions, e.g. {miss[:5]}")
    return {n: str(r[n]) for n in D["parts"]}


# ----------------------------------------------------------------------------------------------------------- geometry
def bbox(rects):
    return (min(r[0] for r in rects), min(r[1] for r in rects), max(r[2] for r in rects), max(r[3] for r in rects))


def rect_gap(a, b):
    return max(0.0, max(a[0], b[0]) - min(a[2], b[2])) + max(0.0, max(a[1], b[1]) - min(a[3], b[3]))


def touch_len(a, b, tol=ADJ_TOL_UM):
    """shared face length of two (near-)abutting rects (0 if they do not face each other within tol)."""
    gx = max(a[0], b[0]) - min(a[2], b[2])
    gy = max(a[1], b[1]) - min(a[3], b[3])
    L = 0.0
    if gx <= tol and gy < 0 and gx > -tol:
        L = -gy
    elif gy <= tol and gx < 0 and gy > -tol:
        L = -gx
    return L if L >= 1.0 else 0.0


def xing_point(ra, rb):
    """midpoint of the closest point pair of two rects (the face midpoint when they abut)."""
    def ax(a0, a1, b0, b1):
        lo, hi = max(a0, b0), min(a1, b1)
        if lo <= hi:
            return (lo + hi) / 2
        return (a1 + b0) / 2 if a1 < b0 else (b1 + a0) / 2
    return (ax(ra[0], ra[2], rb[0], rb[2]), ax(ra[1], ra[3], rb[1], rb[3]))


def region_geom(D, reg):
    mem = collections.defaultdict(list)
    for n, r in reg.items():
        mem[r].append(n)
    G = {}
    for r, ns in mem.items():
        b = bbox([D["parts"][n]["rect"] for n in ns])
        G[r] = dict(parts=sorted(ns), bbox=b, cen=((b[0] + b[2]) / 2, (b[1] + b[3]) / 2), w=b[2] - b[0], h=b[3] - b[1],
                    hard=any(D["parts"][n]["hard"] for n in ns))
    return G


def part_adjacency(D):
    names = sorted(D["parts"])
    rects = [D["parts"][n]["rect"] for n in names]
    out = {}
    for i in range(len(names)):
        ri = rects[i]
        for j in range(i + 1, len(names)):
            L = touch_len(ri, rects[j])
            if L > 0:
                out[(names[i], names[j])] = L
    return out


# ---------------------------------------------------------------------------------------------------------- feed tree
def region_graph(D, reg, padj, xings):
    """region adjacency: shared face length + crossing bits per region pair; components joined by nearest pairs."""
    E = collections.defaultdict(lambda: dict(face_um=0.0, bits=0))
    for (a, b), L in padj.items():
        ra, rb = reg[a], reg[b]
        if ra != rb:
            E[tuple(sorted((ra, rb)))]["face_um"] += L
    for x in xings:
        k = tuple(sorted((x["ra"], x["rb"])))
        if k in E:
            E[k]["bits"] += x["width"]
    return dict(E)


def feed_tree(G, E, xings, v, kind="fwd"):
    """maximum-weight spanning tree (crossing bits, then shorter centre distance) rooted at least eccentricity."""
    nodes = sorted(G)
    edges = sorted(E.items(), key=lambda kv: (-kv[1]["bits"], manh(G[kv[0][0]]["cen"], G[kv[0][1]]["cen"])))
    par = {n: n for n in nodes}

    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a
    adj = collections.defaultdict(list)
    for (a, b), _ in edges:
        if find(a) != find(b):
            par[find(a)] = find(b)
            adj[a].append(b)
            adj[b].append(a)
    # join disconnected components (regions separated by a street wider than ADJ_TOL_UM) by the nearest pair
    joined = []
    while len({find(n) for n in nodes}) > 1:
        best = None
        for a in nodes:
            for b in nodes:
                if a < b and find(a) != find(b):
                    d = rect_gap(G[a]["bbox"], G[b]["bbox"])
                    if best is None or d < best[0]:
                        best = (d, a, b)
        _, a, b = best
        par[find(a)] = find(b)
        adj[a].append(b)
        adj[b].append(a)
        joined.append((a, b))
    taps = tap_points(G, xings)
    adj_all = collections.defaultdict(set)
    for (a, b) in E:
        adj_all[a].add(b)
        adj_all[b].add(a)
    for a, b in joined:
        adj_all[a].add(b)
        adj_all[b].add(a)

    def fwd_delay(p, c):
        t = taps.get((p, c)) or xing_point(G[p]["bbox"], G[c]["bbox"])
        return hop_delay(G, p, c, t, v, kind)

    def build_spt(root):
        T, parent = {root: 0.0}, {root: None}
        pq = [(0.0, root)]
        done = []
        while pq:
            d, u = heapq.heappop(pq)
            if d > T[u] or u in done:
                continue
            done.append(u)
            for c in sorted(adj_all[u]):
                nd = d + fwd_delay(u, c)
                if nd < T.get(c, 1e30) - 1e-9:
                    T[c], parent[c] = nd, u
                    heapq.heappush(pq, (nd, c))
        return parent, done, T

    def build(root):
        if kind == "spt":
            return build_spt(root)
        parent, order, T = {root: None}, [root], {root: 0.0}
        i = 0
        while i < len(order):
            p = order[i]
            i += 1
            for c in sorted(adj[p]):
                if c not in parent:
                    parent[c] = p
                    t = taps.get((p, c)) or xing_point(G[p]["bbox"], G[c]["bbox"])
                    T[c] = T[p] + hop_delay(G, p, c, t, v, kind)
                    order.append(c)
        return parent, order, T
    best = None
    cand = nodes if len(nodes) <= 400 else nodes[:: max(1, len(nodes) // 400)]
    for r in cand:
        parent, order, T = build(r)
        ecc = max(T[n] + ins(G[n], v) for n in nodes)
        if kind in SPINE_FEEDS:  # spine: minimise the longest spine path and the off-tree crossing paths together
            ecc = max(T.values())
        if best is None or ecc < best[0]:
            best = (ecc, r, parent, order)
    _, root, parent, order = best
    tp = {}
    for c, p in parent.items():
        if p is not None:
            tp[(p, c)] = taps.get((p, c)) or xing_point(G[p]["bbox"], G[c]["bbox"])
    return dict(root=root, parent=parent, order=order, tap=tp, joined=joined, kind=kind)


SPINE_FEEDS = ("spine", "fish", "dme")


def hop_delay(G, p, c, t, v, kind):
    """feed delay parent root -> child root.  fwd/spt: from a LEAF of the parent tree (I_p) to the tap, then to the
    child centre.  spine/fish: the spine runs through the parent centre to the tap and on to the child centre (the
    region trees hang off the spine at their centres; no parent insertion on the path)."""
    if kind in SPINE_FEEDS:
        return v * (manh(G[p]["cen"], t) + manh(t, G[c]["cen"])) / 1000.0
    return ins(G[p], v) + v * manh(t, G[c]["cen"]) / 1000.0


def leaf_delay(g, xy, v, kind):
    """region root -> entry at xy.  H-tree region tree: equal length I; fishbone region tree (feed 'fish'): spine
    along the long axis through the centre + perpendicular rib = Manhattan distance (nominal d follows position)."""
    if kind == "fish" and not g.get("virtual"):
        return v * manh(xy, g["cen"]) / 1000.0
    return ins(g, v)


def fish_shared_um(g, p, q):
    """fishbone region tree (spine on the long axis through the centre, ribs perpendicular): the length from the
    centre that the paths to p and q share (same side of the spine centre: up to the nearer rib; same rib: + the
    shorter rib part on the same side)."""
    ax = 0 if g["w"] >= g["h"] else 1
    c = g["cen"]
    ap, aq = p[ax] - c[ax], q[ax] - c[ax]
    if ap * aq <= 0:
        return 0.0
    s = min(abs(ap), abs(aq))
    if abs(ap - aq) <= LEAF_UM:
        rp, rq = p[1 - ax] - c[1 - ax], q[1 - ax] - c[1 - ax]
        if rp * rq > 0:
            s += min(abs(rp), abs(rq))
    return s


def tap_points(G, xings):
    acc = collections.defaultdict(lambda: [0.0, 0.0, 0])
    for x in xings:
        for k in ((x["ra"], x["rb"]), (x["rb"], x["ra"])):
            a = acc[k]
            a[0] += x["xy"][0] * x["width"]
            a[1] += x["xy"][1] * x["width"]
            a[2] += x["width"]
    return {k: (a[0] / a[2], a[1] / a[2]) for k, a in acc.items() if a[2]}


def top_tree(G, v):
    """the die-wide balanced form: a virtual TOP region whose leaves are the region roots."""
    cs = [g["cen"] for g in G.values()]
    b = (min(x for x, _ in cs), min(y for _, y in cs), max(x for x, _ in cs), max(y for _, y in cs))
    top = dict(parts=[], bbox=b, cen=((b[0] + b[2]) / 2, (b[1] + b[3]) / 2), w=b[2] - b[0], h=b[3] - b[1], hard=False,
               virtual=True)
    parent = {"__TOP__": None}
    parent.update({r: "__TOP__" for r in G})
    tap = {("__TOP__", r): G[r]["cen"] for r in G}
    return top, dict(root="__TOP__", parent=parent, order=["__TOP__"] + sorted(G), tap=tap, joined=[])


def ins(g, v):
    return v * (g["w"] + g["h"]) / 2.0 / 1000.0


def dme_heights(G, F, v):
    """zero-skew (DME) spine on the feed tree: h(r) = delay from r's spine node to every leaf below it (its own
    region tree padded up to h(r)); h(r) = max(I_r, max_c spine(r, c) + h(c))."""
    h = {}
    for r in reversed(F["order"]):
        kids = [c for c in F["order"] if F["parent"][c] == r]
        h[r] = max([ins(G[r], v)] + [hop_delay(G, r, c, F["tap"][(r, c)], v, "spine") + h[c] for c in kids])
    return h


def arrivals(G, F, v, period=None):
    """root arrival per region (TT ps); with period, whole-cycle pads so each child's leaves sit on its parent's grid.
    dme: spine-node arrivals of the zero-skew spine (every leaf at h(root), nominal d = 0)."""
    T, pad = {}, {}
    if F.get("kind") == "dme":
        h = F.setdefault("h", dme_heights(G, F, v))
        for r in F["order"]:
            p = F["parent"][r]
            T[r] = 0.0 if p is None else T[p] + h[p] - h[r]
            pad[r] = 0.0 if p is None else h[p] - h[r] - hop_delay(G, p, r, F["tap"][(p, r)], v, "spine")
        return T, pad
    imax = max((ins(g, v) for g in G.values() if not g.get("virtual")), default=0.0)
    for r in F["order"]:
        p = F["parent"][r]
        if p is None:
            T[r], pad[r] = 0.0, 0.0
            continue
        base = T[p] + hop_delay(G, p, r, F["tap"][(p, r)], v, F.get("kind", "fwd"))
        pad[r] = 0.0
        if G[p].get("virtual"):  # the balanced die tree: every region's leaves at the same arrival (delay = unshared)
            base += imax - ins(G[r], v)
        if period:
            leaf = base + ins(G[r], v)
            pad[r] = (-(leaf - (T[p] + ins(G[p], v)))) % period
        T[r] = base + pad[r]
    return T, pad


LEAF_UM = 50.0


def htree_rem_um(box, p, q):
    """H-tree (recursive bisection of the longer side at the centre) from the box centre: the path length left below
    the node where leaves p and q part = (w + h) / 2 of that node's box (the root box if the first cut separates them)."""
    x0, y0, x1, y1 = box
    while True:
        w, h = x1 - x0, y1 - y0
        if max(w, h) <= LEAF_UM:
            return (w + h) / 2
        if w >= h:
            m = (x0 + x1) / 2
            if (p[0] < m) != (q[0] < m):
                return (w + h) / 2
            x0, x1 = (x0, m) if p[0] < m else (m, x1)
        else:
            m = (y0 + y1) / 2
            if (p[1] < m) != (q[1] < m):
                return (w + h) / 2
            y0, y1 = (y0, m) if p[1] < m else (m, y1)


def lineage(F, r):
    out = [r]
    while F["parent"][out[-1]] is not None:
        out.append(F["parent"][out[-1]])
    return out


def branches(G, F, T, v, x):
    """unshared clock (TT ps) of both entries of crossing x, the last common point and the bbox points."""
    A, B = x["ra"], x["rb"]
    la, lb = lineage(F, A), lineage(F, B)
    sb = set(lb)
    L = next(r for r in la if r in sb)
    pA = x["xy"] if A == L else F["tap"][(L, la[la.index(L) - 1])]
    pB = x["xy"] if B == L else F["tap"][(L, lb[lb.index(L) - 1])]
    kind = F.get("kind", "fwd")
    IL = ins(G[L], v)
    if kind in ("spine", "dme"):  # H-tree region trees hang off the spine at the centre: every path parts there
        div = T[L]
    elif kind == "fish" and not G[L].get("virtual"):
        div = T[L] + v * fish_shared_um(G[L], pA, pB) / 1000.0
    else:
        div = T[L] + IL - min(IL, v * htree_rem_um(G[L]["bbox"], pA, pB) / 1000.0)
    if kind == "dme":
        aa, ab = T[A] + F["h"][A], T[B] + F["h"][B]
    else:
        aa = T[A] + leaf_delay(G[A], x["xy"], v, kind)
        ab = T[B] + leaf_delay(G[B], x["xy"], v, kind)
    ua, ub = aa - div, ab - div
    pts = [x["xy"], pA, pB] + [G[r]["cen"] for r in la[:la.index(L)] + lb[:lb.index(L)]]
    return dict(lca=L, ua=ua, ub=ub, div=div, arr_a=aa, arr_b=ab, pts=pts, far=x.get("far", False),
                tree_hops=la.index(L) + lb.index(L))


# ------------------------------------------------------------------------------------------------------------- margin
def margins(br_rows, Ttab, period, budget=None, ff_scale=None):
    """per crossing TT/FF margins with the shared model: landed_phase_ocv.analyse on a synthetic tree."""
    budget = period / 2 if budget is None else budget
    if ff_scale is None:
        ff_scale = Ttab["classes"]["A"]["FF"]["mu_stage_ps"] / Ttab["classes"]["A"]["TT"]["mu_stage_ps"]
    out = {}
    for corner, s in (("TT", 1.0), ("FF", ff_scale)):
        mu = Ttab["classes"]["A"][corner]["mu_stage_ps"]
        tree = dict(taps=[], node_buf={}, parent_of={}, sites={})
        Ta, Na, ports = {}, {}, []
        nid = 0
        for i, b in enumerate(br_rows):
            lca = f"L{i}"
            xs = [p[0] for p in b["pts"]]
            ys = [p[1] for p in b["pts"]]
            tree["sites"][lca] = [(min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2]
            Na[lca] = b["div"] * s
            for side, u, xy in (("a", b["ua"], (min(xs), min(ys))), ("b", b["ub"], (max(xs), max(ys)))):
                n = max(1, int(round(u * s / mu)))
                prev = lca
                for k in range(n):
                    c = f"{side}{i}_{k}"
                    tree["parent_of"][c] = prev
                    tree["sites"][c] = list(xy)
                    prev = c
                nid += 1
                tree["node_buf"][str(nid)] = prev
                part = f"x{i}{side}"
                tree["taps"].append(dict(port=f"{part}__clk", part=part, xy=list(xy), node=nid))
                Ta[f"{part}__clk"] = (b["div"] + u) * s
            ports.append(dict(id=str(i), src=dict(part=f"x{i}a"), dst=dict(part=f"x{i}b")))
        rows = LP.analyse(dict(ports=ports), tree, (Ta, Na), CA, Ttab, corner, CORE_LAT[corner], budget, "regions")
        out[corner] = {int(r["port"]): r for r in rows}
    res = []
    for i, b in enumerate(br_rows):
        t, f = out["TT"][i], out["FF"][i]
        k = round(((t["d_ps"] + f["d_ps"]) / 2) / period)

        def m(r, d):
            return round(budget - max(abs(d + r["p_up_ps"]), abs(d - r["p_dn_ps"])), 1)
        res.append(dict(unshared_tt=round(max(b["ua"], b["ub"]), 1), d_tt=t["d_ps"], d_ff=f["d_ps"], k=k,
                        p_tt=round(max(t["p_up_ps"], t["p_dn_ps"]), 1), p_ff=round(max(f["p_up_ps"], f["p_dn_ps"]), 1),
                        raw_tt=t["margin_ps"], raw_ff=f["margin_ps"],
                        fold_tt=m(t, t["d_ps"] - k * period), fold_ff=m(f, f["d_ps"] - k * period),
                        ca_tt=round(budget - max(t["p_up_ps"], t["p_dn_ps"]), 1),
                        ca_ff=round(budget - max(f["p_up_ps"], f["p_dn_ps"]), 1),
                        dist_um=t["dist_um"]))
    return res


# -------------------------------------------------------------------------------------------------------------- score
def crossings(D, reg, G, padj):
    radj = {tuple(sorted((reg[a], reg[b]))) for (a, b) in padj if reg[a] != reg[b]}
    out = []
    for q in D["ports"]:
        ra, rb = reg[q["src"]], reg[q["dst"]]
        if ra == rb:
            continue
        xy = xing_point(D["parts"][q["src"]]["rect"], D["parts"][q["dst"]]["rect"])
        out.append(dict(id=q["id"], src=q["src"], dst=q["dst"], ra=ra, rb=rb, width=q["width"], xy=xy,
                        far=tuple(sorted((ra, rb))) not in radj))
    return out


def tracks(G, E, xings, face_pins_per_um):
    """route each region pair's bits on the adjacency graph (shortest centre path); demand vs face pin supply."""
    adj = collections.defaultdict(list)
    for (a, b) in E:
        if E[(a, b)]["face_um"] > 0:
            w = manh(G[a]["cen"], G[b]["cen"])
            adj[a].append((b, w))
            adj[b].append((a, w))
    load = collections.Counter()
    pairbits = collections.Counter()
    for x in xings:
        pairbits[(x["ra"], x["rb"])] += x["width"]
    hops = collections.Counter()
    unrouted = 0
    cache = {}
    for (a, b), bits in pairbits.items():
        if a not in cache:
            dist, prev = {a: 0.0}, {}
            pq = [(0.0, a)]
            while pq:
                d, u = heapq.heappop(pq)
                if d > dist[u]:
                    continue
                for nb, wt in adj[u]:
                    nd = d + wt
                    if nd < dist.get(nb, 1e30):
                        dist[nb], prev[nb] = nd, u
                        heapq.heappush(pq, (nd, nb))
            cache[a] = prev
        prev = cache[a]
        if b not in prev:
            unrouted += bits
            continue
        n, path = b, []
        while n != a:
            path.append(tuple(sorted((n, prev[n]))))
            n = prev[n]
        for e in path:
            load[e] += bits
        hops[len(path)] += bits
    rows = []
    for e, bits in load.items():
        sup = face_pins_per_um * E[e]["face_um"]
        rows.append(dict(pair=list(e), bits=bits, face_um=round(E[e]["face_um"], 1), supply=round(sup),
                         ratio=round(bits / sup, 3) if sup else None))
    rows.sort(key=lambda r: -(r["ratio"] or 0))
    return dict(worst=rows[:10], over_1=sum(1 for r in rows if (r["ratio"] or 0) > 1.0), boundaries=len(rows),
                unrouted_bits=unrouted, bits_by_hops=dict(sorted(hops.items())))


def score(D, reg, v, feed="fwd", padj=None, M=None, Ttab=None):
    padj = part_adjacency(D) if padj is None else padj
    M = traffic(D) if M is None else M
    Ttab = CA.load(TABLE) if Ttab is None else Ttab
    G = region_geom(D, reg)
    X = crossings(D, reg, G, padj)
    E = region_graph(D, reg, padj, X)
    ins_bits = sum(m["bits"] for (a, b), m in M.items() if reg[a] == reg[b])
    ins_bm = sum(m["bitmm"] for (a, b), m in M.items() if reg[a] == reg[b])
    tot_bits = sum(m["bits"] for m in M.values())
    tot_bm = sum(m["bitmm"] for m in M.values())
    if feed == "top":
        top, F = top_tree(G, v)
        G = dict(G)
        G["__TOP__"] = top
    else:
        F = feed_tree(G, E, X, v, feed)
    readings = {}
    per = None
    for mode in ("nopad", "pad"):
        if mode == "pad" and (feed == "top" or feed in SPINE_FEEDS):
            continue
        Tr, pad = arrivals(G, F, v, D["period"] if mode == "pad" else None)
        BR = [branches(G, F, Tr, v, x) for x in X]
        R = margins(BR, Ttab, D["period"]) if BR else []
        for x, b, r in zip(X, BR, R):
            on = F["parent"].get(x["ra"]) == x["rb"] or F["parent"].get(x["rb"]) == x["ra"]
            r.update(id=x["id"], ra=x["ra"], rb=x["rb"], width=x["width"], xy=[round(c, 1) for c in x["xy"]],
                     lca=b["lca"], far=x["far"], on_feed=on, tree_hops=b["tree_hops"])
        readings[mode] = (R, pad)
        if mode == "nopad":
            per = R
            if feed != "top":
                hop = hop_rows(G, F, Tr, v, X, R, Ttab, D["period"])
    real = {r: g for r, g in G.items() if not g.get("virtual")}
    regs = [dict(region=r, parts=len(g["parts"]), w_mm=round(g["w"] / 1000, 2), h_mm=round(g["h"] / 1000, 2),
                 ins_ps=round(ins(g, v), 1), hard=g["hard"]) for r, g in sorted(real.items())]

    def worst(R, key):  # no crossing at all: nothing to violate -> the full budget P/2
        return min((r[key] for r in R), default=round(D["period"] / 2, 1))

    def under(R, key, t):
        return sum(1 for r in R if r[key] < t)
    summ = dict(feed=feed, v_ps_per_mm=v, regions=len(real), partitions=len(D["parts"]),
                bits_total=tot_bits, bits_inside=ins_bits, bits_across=tot_bits - ins_bits,
                frac_bits_inside=round(ins_bits / tot_bits, 4) if tot_bits else None,
                bitmm_total=round(tot_bm, 1), bitmm_inside=round(ins_bm, 1), bitmm_across=round(tot_bm - ins_bm, 1),
                frac_bitmm_inside=round(ins_bm / tot_bm, 4) if tot_bm else None,
                crossing_ports=len(X), crossing_pairs=len({(x["ra"], x["rb"]) for x in X}),
                far_ports=sum(1 for x in X if x["far"]), far_bits=sum(x["width"] for x in X if x["far"]),
                max_span_mm=max((max(g["w"], g["h"]) / 1000 for g in real.values()), default=0),
                max_ins_ps=max((ins(g, v) for g in real.values()), default=0),
                feed_root=F["root"], feed_joined=len(F["joined"]),
                worst_unshared_tt=max((r["unshared_tt"] for r in per), default=0),
                off_feed_ports=sum(1 for r in per if not r["on_feed"]),
                off_feed_bits=sum(r["width"] for r in per if not r["on_feed"]),
                worst_unshared_on_feed_tt=max((r["unshared_tt"] for r in per if r["on_feed"]), default=0),
                worst_unshared_off_feed_tt=max((r["unshared_tt"] for r in per if not r["on_feed"]), default=0),
                loop_pairs=len({(r["ra"], r["rb"]) for r in per if not r["on_feed"]}),
                max_tree_hops=max((r["tree_hops"] for r in per), default=0))
    if feed != "top":
        HR, hst = hop
        summ.update(hst)
        for kname in ("raw", "ca", "fold"):
            for c in ("tt", "ff"):
                summ[f"hop_{kname}_worst_{c}"] = min((r[f"{kname}_{c}"] for r in HR), default=round(D["period"] / 2, 1))
                summ[f"hop_{kname}_under100_{c}"] = sum(1 for r in HR if r[f"{kname}_{c}"] < 100)
    for mode, (R, pad) in readings.items():
        keys = (("raw", "fold", "ca") if mode == "nopad" else ("pad",))
        for kname in keys:
            src = "fold" if kname == "pad" else kname  # (PAD rows carry the padded d in fold_*)
            for c in ("tt", "ff"):
                summ[f"{kname}_worst_{c}"] = worst(R, f"{src}_{c}")
                summ[f"{kname}_under100_{c}"] = under(R, f"{src}_{c}", 100)
        if mode == "pad":
            summ["pad_worst_unshared_tt"] = max((r["unshared_tt"] for r in R), default=0)
            summ["pad_max_ps"] = round(max(pad.values(), default=0), 1)
    trk = tracks(real, {k: e for k, e in E.items()}, X, D["face_pins_per_um"])
    summ["tracks_over_1"] = trk["over_1"]
    summ["tracks_worst_ratio"] = trk["worst"][0]["ratio"] if trk["worst"] else None
    return dict(summary=summ, regions=regs, feed=dict(root=F["root"], parent=F["parent"], joined=F["joined"],
                                                      tap={f"{a}->{b}": [round(c, 1) for c in t]
                                                           for (a, b), t in F["tap"].items()}),
                crossings=per, crossings_pad=readings.get("pad", ([], {}))[0], tracks=trk, G=G, F=F,
                crossings_hop=hop[0] if feed != "top" else [])


def hop_rows(G, F, Tr, v, X, R, Ttab, period):
    """12.13c HOP reading: every off-feed (loop-closing or far) crossing is re-timed as a hop chain along the feed-tree
    path between its regions (one fixed-latency landing per tree edge), so only feed parent<->child crossings remain:
    the direct on-feed rows + one synthetic crossing at the tap of every feed edge that carries hop bits without a
    direct crossing.  Cost = latency: hops - 1 extra landings per chain (reported as bit-hops / max hops)."""
    on = [r for r in R if r["on_feed"]]
    direct = {tuple(sorted((r["ra"], r["rb"]))) for r in on}
    load = collections.Counter()
    extra_bh, max_h, n_off = 0, 0, 0
    for x, r in zip(X, R):
        if r["on_feed"]:
            continue
        n_off += 1
        la, lb = lineage(F, x["ra"]), lineage(F, x["rb"])
        sb = set(lb)
        L = next(q for q in la if q in sb)
        path = la[:la.index(L)] + lb[:lb.index(L)]  # each region below L = one tree edge to its parent
        for c in path:
            load[(F["parent"][c], c)] += x["width"]
        max_h = max(max_h, len(path))
        extra_bh += x["width"] * (len(path) - 1)
    syn = []
    for (p, c), bits in sorted(load.items()):
        if tuple(sorted((p, c))) in direct:
            continue
        syn.append(dict(id=f"hop:{p}>{c}", src=p, dst=c, ra=p, rb=c, width=bits, xy=F["tap"][(p, c)], far=False))
    rows = list(on)
    if syn:
        BR = [branches(G, F, Tr, v, x) for x in syn]
        for x, b, m in zip(syn, BR, margins(BR, Ttab, period)):
            m.update(id=x["id"], ra=x["ra"], rb=x["rb"], width=x["width"], xy=[round(c, 1) for c in x["xy"]],
                     lca=b["lca"], far=False, on_feed=True, tree_hops=b["tree_hops"], synthetic=True)
            rows.append(m)
    return rows, dict(hop_chains=n_off, hop_max_hops=max_h, hop_extra_bit_hops=extra_bh, hop_synthetic_edges=len(syn))


# ------------------------------------------------------------------------------------------------------------ propose
def propose(D, span_mm=3.5, M=None, padj=None):
    """greedy connectivity clustering under the span cap; hard partitions join their port neighbours first."""
    M = traffic(D) if M is None else M
    padj = part_adjacency(D) if padj is None else padj
    parts = D["parts"]
    cap = span_mm * 1000.0
    cl = {n: {n} for n in parts}
    of = {n: n for n in parts}
    box = {n: parts[n]["rect"] for n in parts}

    def fits(b, members):
        if max(b[2] - b[0], b[3] - b[1]) > cap + 1e-6:
            return False
        for n, p in parts.items():
            if n in members:
                continue
            cx, cy = p["cen"]
            if b[0] < cx < b[2] and b[1] < cy < b[3]:
                return False
        return True

    def merge(a, b):
        cl[a] |= cl[b]
        for n in cl[b]:
            of[n] = a
        box[a] = bbox([box[a], box[b]])
        del cl[b], box[b]
    # hard partitions (no landing ring inside): join every port neighbour when the span allows it
    for n, p in sorted(parts.items()):
        if not p["hard"]:
            continue
        nb = sorted({b if a == n else a for (a, b) in M if n in (a, b)})
        for m in nb:
            a, b = of[n], of[m]
            if a != b:
                nbx = bbox([box[a], box[b]])
                if fits(nbx, cl[a] | cl[b]):
                    merge(a, b)
    W = collections.Counter()
    for (a, b), m in M.items():
        W[(a, b)] += m["bits"]
    bad = set()  # cluster pairs that failed: boxes only grow, so they stay failed until one side merges
    while True:
        cw = collections.Counter()
        for (a, b), w in W.items():
            ca, cb = of[a], of[b]
            if ca != cb:
                cw[tuple(sorted((ca, cb)))] += w
        done = False
        for (a, b), w in sorted(cw.items(), key=lambda kv: (-kv[1], kv[0])):
            if (a, b) in bad:
                continue
            nbx = bbox([box[a], box[b]])
            if fits(nbx, cl[a] | cl[b]):
                merge(a, b)
                bad = {k for k in bad if a not in k and b not in k}
                done = True
                break
            bad.add((a, b))
        if not done:
            break
    names = {}
    for k in sorted(cl, key=lambda k: (round(box[k][1], -2), box[k][0])):
        names[k] = f"R{len(names):03d}"
    return {n: names[of[n]] for n in parts}


def loop_stats(of, M, padj):
    """crossing graph of a partition -> cluster map: the feed tree is the maximum-bit spanning forest of the cluster
    ADJACENCY graph (weight = crossing bits); every crossing cluster pair that is not a tree edge closes a loop
    (off-feed).  Returns (loop bits, loop pairs, tree edge set, pair bits)."""
    cw = collections.Counter()
    for (a, b), m in M.items():
        ca, cb = of[a], of[b]
        if ca != cb:
            cw[(ca, cb) if ca < cb else (cb, ca)] += m["bits"]
    adjc = set()
    for (a, b) in padj:
        ca, cb = of[a], of[b]
        if ca != cb:
            adjc.add((ca, cb) if ca < cb else (cb, ca))
    par = {}

    def find(a):
        par.setdefault(a, a)
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a
    tree = set()
    for e in sorted(adjc, key=lambda e: (-cw.get(e, 0), e)):
        ra, rb = find(e[0]), find(e[1])
        if ra != rb:
            par[ra] = rb
            tree.add(e)
    loop = {e: w for e, w in cw.items() if e not in tree}
    return sum(loop.values()), len(loop), tree, cw


def propose_tree(D, span_mm=2.0, cap_mm=3.5, M=None, padj=None, max_iter=400):
    """proposer v2 (12.13 b/c): start from the connectivity map (propose, span_mm) and make the region CROSSING GRAPH
    a tree (or near-tree: chain / fishbone along the dataflow) so that every crossing joins a feed parent and child.
    (1) MERGE: for each loop-closing cluster pair (heaviest first) merge the two clusters -- or, failing that, the
        whole fundamental cycle (the pair + the feed-tree path between them: the loop closes inside one region) --
        absorbing every cluster that lies wholly inside the merged box, when the box side stays <= cap_mm and no
        foreign partition centre is inside; kept only if the loop-closing bits drop.
    (2) RE-CUT: move one end partition of a loop-closing pair into the other cluster (same box rules), kept only if the
        loop-closing bits drop.
    The remaining loop-closing crossings are counted and reported (off-feed)."""
    M = traffic(D) if M is None else M
    padj = part_adjacency(D) if padj is None else padj
    parts = D["parts"]
    cap = cap_mm * 1000.0
    of = dict(propose(D, span_mm, M, padj))
    cl = collections.defaultdict(set)
    for n, r in of.items():
        cl[r].add(n)

    def box_of(ns):
        return bbox([parts[n]["rect"] for n in ns])

    def legal(ns):
        b = box_of(ns)
        if max(b[2] - b[0], b[3] - b[1]) > cap + 1e-6:
            return False
        for n, p in parts.items():
            if n not in ns and b[0] < p["cen"][0] < b[2] and b[1] < p["cen"][1] < b[3]:
                return False
        return True

    def absorb(ns):
        """grow ns by every cluster wholly inside its box (to a fixpoint); None if a partly-inside cluster blocks."""
        ns = set(ns)
        while True:
            b = box_of(ns)
            if max(b[2] - b[0], b[3] - b[1]) > cap + 1e-6:
                return None
            inside = {n for n, p in parts.items() if n not in ns and b[0] < p["cen"][0] < b[2]
                      and b[1] < p["cen"][1] < b[3]}
            if not inside:
                return ns
            for r in {of[n] for n in inside}:
                if not cl[r] <= (inside | ns):
                    return None
                ns |= cl[r]
    best, npairs, _, _ = loop_stats(of, M, padj)
    log = [("start", best, npairs, len(cl))]
    it = 0
    improved = True
    while improved and it < max_iter:
        improved = False
        _, _, tree, cw = loop_stats(of, M, padj)
        loops = sorted(((w, e) for e, w in cw.items() if e not in tree), reverse=True)
        tadj = collections.defaultdict(set)
        for x, y in tree:
            tadj[x].add(y)
            tadj[y].add(x)

        def tree_path(a, b):
            prev, q = {a: None}, [a]
            for u in q:
                if u == b:
                    break
                for w2 in tadj[u]:
                    if w2 not in prev:
                        prev[w2] = u
                        q.append(w2)
            if b not in prev:
                return [a, b]
            out = [b]
            while prev[out[-1]] is not None:
                out.append(prev[out[-1]])
            return out
        for w, (a, b) in loops:
            it += 1
            ok = None
            for group in ([a, b], tree_path(a, b)):
                ns = absorb(set().union(*(cl[r] for r in group)))
                if ns is None or not legal(ns):
                    continue
                trial = dict(of)
                for n in ns:
                    trial[n] = a
                lb, lp, _, _ = loop_stats(trial, M, padj)
                if lb < best:
                    ok = (trial, lb, lp, ns)
                    break
            if ok:
                trial, lb, lp, ns = ok
                for r in {of[n] for n in ns} - {a}:
                    del cl[r]
                cl[a] = set(ns)
                of, best, npairs = trial, lb, lp
                improved = True
                log.append(("merge", best, npairs, len(cl)))
                break
        if improved:
            continue
        # re-cut: move one end partition of a loop pair to the other side
        pp = collections.defaultdict(list)
        for (x, y), m in M.items():
            e = tuple(sorted((of[x], of[y])))
            if e[0] != e[1]:
                pp[e].append((m["bits"], x, y))
        for w, e in loops:
            for _, x, y in sorted(pp.get(e, []), reverse=True)[:4]:
                for mv, dst in ((x, of[y]), (y, of[x])):
                    src = of[mv]
                    if len(cl[src]) == 1 or not legal(cl[dst] | {mv}):
                        continue
                    trial = dict(of)
                    trial[mv] = dst
                    lb, lp, _, _ = loop_stats(trial, M, padj)
                    if lb < best:
                        cl[src].discard(mv)
                        cl[dst].add(mv)
                        of, best, npairs = trial, lb, lp
                        improved = True
                        log.append(("recut", best, npairs, len(cl)))
                        break
                if improved:
                    break
            if improved:
                break
    names = {}
    for k in sorted((k for k in cl if cl[k]), key=lambda k: (round(box_of(cl[k])[1], -2), box_of(cl[k])[0])):
        names[k] = f"T{len(names):03d}"
    return {n: names[of[n]] for n in parts}, log


# ------------------------------------------------------------------------------------------------------------- render
def key_rows(S, key):
    """rows and per-row key of a v2 reading: hop_* readings use the hop-chain rows (on-feed + synthetic edges)."""
    if key.startswith("hop_"):
        S["_hop"] = True
        return S["crossings_hop"], key[4:]
    S["_hop"] = False
    return S["crossings"], key


def render(D, S, path, title, key=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    G, F = S["G"], S["F"]
    W, H = D["outline"]
    fig, ax = plt.subplots(figsize=(10, 10 * H / W if W else 10), dpi=110)
    cmap = plt.get_cmap("tab20")
    reg_ids = {r: i for i, r in enumerate(sorted(r for r in G if not G[r].get("virtual")))}
    for n, p in D["parts"].items():
        x0, y0, x1, y1 = p["rect"]
        r = S["_reg"][n]
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor=cmap(reg_ids[r] % 20), alpha=0.55,
                               edgecolor="#555", lw=0.2, hatch="//" if p["hard"] else None))
    for r, g in G.items():
        if g.get("virtual"):
            continue
        b = g["bbox"]
        ax.add_patch(Rectangle((b[0], b[1]), g["w"], g["h"], fill=False, edgecolor="k", lw=0.9))
    for (p, c), t in F["tap"].items():
        pc = G[p]["cen"] if not G[p].get("virtual") else G[p]["cen"]
        ax.plot([pc[0], t[0], G[c]["cen"][0]], [pc[1], t[1], G[c]["cen"][1]], color="#1f4fd1", lw=0.8, alpha=0.8)
    rc = G[F["root"]]["cen"]
    ax.plot([rc[0]], [rc[1]], marker="*", color="#1f4fd1", ms=14)
    rows = S["crossings_pad"] or S["crossings"]
    if key:
        rows, key = key_rows(S, key)
    agg = {}
    for r in rows:
        m = min(r[f"{key or 'fold'}_tt"], r[f"{key or 'fold'}_ff"])
        k = (r["ra"], r["rb"])
        a = agg.setdefault(k, [r["xy"], m, 0, r["far"]])
        a[1] = min(a[1], m)
        a[2] += r["width"]
    for (ra, rb), (xy, m, bits, far) in agg.items():
        col = "#c0392b" if m < 0 else ("#e67e22" if m < 100 else "#1e8449")
        ax.plot([xy[0]], [xy[1]], marker="o" if not far else "x", color=col,
                ms=2.5 + 6 * min(1.0, math.sqrt(bits / 20000.0)), mec="k" if not far else col, mew=0.4)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")
    s = S["summary"]
    rd = ({"ca": "COUNT-ALIGNED", "raw": "CURRENT RING", "fold": "STATIC COUNT"}.get(key, "")
          + (" + HOP CHAINS" if S.get("_hop") else "")) or ("PAD" if S["crossings_pad"] else "FOLD")
    ax.set_title(f"{title}\n{s['regions']} regions, bit-mm inside {100 * (s['frac_bitmm_inside'] or 0):.1f} %, "
                 f"{s['crossing_ports']} crossing ports ({s['far_ports']} far), feed {s['feed']}; "
                 f"dots = crossings by min({rd} TT,FF) margin: green >=100, orange <100, red <0; x = far",
                 fontsize=8)
    ax.tick_params(labelsize=6)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


# -------------------------------------------------------------------------------------------------------- estimate md
def estimate_md(die, v, runs, D):
    L = [f"# 12.14b ESTIMATE: {die} region map / clock feed / crossings (LOCALITY-SCORE-1, analytic, UNCHECKED)", "",
         f"Inputs: plan {D['_plan']} (sha256 {D['_sha'][:12]}), {len(D['parts'])} partitions, {len(D['ports'])} ports; "
         f"trunk delay v = {v:g} ps/mm TT (measured, see LOCALITY.md); P = {D['period']:g} ps, budget P/2; "
         f"face supply {D['face_pins_per_um']:g} pins/um.",
         "Model: tools/die_plan/locality.py docstring (equal-length region trees from the box centre, I = v (w+h)/2; "
         "fwd = neighbour-forwarded max-bit spanning tree, top = one balanced die H-tree; margins by "
         "landed_phase_ocv.analyse with clk_aocv g021 + droop regions + core latency class B). Off-feed = a crossing "
         "whose two regions are not parent/child in the feed tree (its last common point sits up the tree).",
         "Calibration (CHECKED vs measured, top feed): HEAD part map -59.9 TT / +17.2 FF, 33 < 100 vs LAND-HEAD-2 d=0 "
         "bound -60.7 / +13.3, 33 < 100; KV land128 -52.5 / +23.7 vs LAND-KV-1 perfect-balance bound -136.4 / -47.1 "
         "(model 6.2 ns unshared vs 7.2 ns built: the model is ~70-85 ps optimistic where the built tree is deeper "
         "than an ideal H-tree).", "",
         "| map | feed | regions | max span mm | max I ns | bit-mm inside | crossing ports / pairs | far ports | off-feed ports | "
         "worst unshared ns | RAW TT/FF | FOLD TT/FF | PAD TT/FF (unsh. ns, max pad) | FOLD <100 TT/FF | PAD <100 TT/FF | "
         "track ratio worst (>1) |",
         "|" + "---|" * 16]
    for name, S in runs:
        s = S["summary"]

        def f(a, b):
            return "-" if s.get(a) is None else f"{s[a]:.0f} / {s[b]:.0f}"
        pad = ("-" if "pad_worst_tt" not in s else
               f"{s['pad_worst_tt']:.0f} / {s['pad_worst_ff']:.0f} ({s['pad_worst_unshared_tt'] / 1000:.2f}, "
               f"{s['pad_max_ps']:.0f})")
        padu = "-" if "pad_under100_tt" not in s else f"{s['pad_under100_tt']} / {s['pad_under100_ff']}"
        L.append(f"| {name} | {s['feed']} | {s['regions']} | {s['max_span_mm']:.2f} | {s['max_ins_ps'] / 1000:.2f} | "
                 f"{100 * (s['frac_bitmm_inside'] or 0):.1f} % | {s['crossing_ports']} / {s['crossing_pairs']} | "
                 f"{s['far_ports']} | {s['off_feed_ports']} | {s['worst_unshared_tt'] / 1000:.2f} | "
                 f"{f('raw_worst_tt', 'raw_worst_ff')} | "
                 f"{f('fold_worst_tt', 'fold_worst_ff')} | {pad} | {s['fold_under100_tt']} / {s['fold_under100_ff']} | "
                 f"{padu} | {s['tracks_worst_ratio']} ({s['tracks_over_1']}) |")
    L += ["", "Readings: RAW = today's ring with unfolded nominal d; FOLD = count-aligned crossing (d - kP, one k for TT "
          "and FF); PAD = forwarded hops padded to whole cycles at TT (pad = clock delay, charged as unshared). The gate "
          "stays 12.13d (measured landed_phase_ocv >= 100 ps TT and FF on every crossing after GRT).", ""]
    for name, S in runs:
        s = S["summary"]
        rows = S["crossings_pad"] or S["crossings"]
        if not rows:
            continue
        worst = sorted(rows, key=lambda r: min(r["fold_tt"], r["fold_ff"]))[:5]
        L.append(f"Worst crossings, {name} ({s['feed']}, {'PAD' if S['crossings_pad'] else 'FOLD'}): " + "; ".join(
            f"{r['ra']}->{r['rb']} {r['width']} b, unshared {r['unshared_tt'] / 1000:.2f} ns, d {r['d_tt']:.0f}, "
            f"p {r['p_tt']:.0f}/{r['p_ff']:.0f}, margin {r['fold_tt']:.0f}/{r['fold_ff']:.0f}" for r in worst))
        t = S["tracks"]["worst"][:3]
        if t:
            L.append(f"  Tracks: worst boundaries " + "; ".join(
                f"{'|'.join(x['pair'])} {x['bits']} b over {x['face_um']} um face = {x['ratio']}x supply" for x in t)
                + f"; crossing bits by region hops {S['tracks']['bits_by_hops']}")
    L += ["", "Verdict rule (12.14b): build a map/feed only if its estimated PAD or FOLD margin is >= 100 ps TT and FF "
          "on every crossing and its track ratio is <= 1; otherwise fix the map (smaller span, cut along low-traffic "
          "seams) first. Every number on this page is an ESTIMATE (UNCHECKED) until a GRT + landed_phase_ocv run."]
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------------------------------------------------- v2 run
MODES = (("ring", "raw", "current ring: phase-dependent, the nominal d counts"),
         ("ca", "ca", "count-aligned: nominal d absorbed by the ring count, only the derated variation counts"),
         ("ring+hop", "hop_raw", "current ring, off-feed crossings re-timed as hop chains along the feed tree (12.13c)"),
         ("ca+hop", "hop_ca", "count-aligned, off-feed crossings re-timed as hop chains along the feed tree (12.13c)"),
         ("static", "fold", "static count: one whole-cycle k per crossing for TT and FF (no reset-time training)"),
         ("static+hop", "hop_fold", "static count + hop chains"))


def run_v2(plan, die, v, out, maps_in=(), tree_cfgs=((2.0, 3.5), (3.5, 5.0)), span=3.5,
           feeds=("fwd", "spine", "fish", "dme", "top"), render_png=True, calib=None):
    """LOCALITY-SCORE-2: every map (given + v1 proposed + tree proposer v2) x feed, margins in both ring modes; per
    die the best map/feed per mode; ESTIMATE page + renders (best per mode)."""
    import hashlib
    D = load_plan(plan)
    D["_plan"] = str(plan)
    D["_sha"] = hashlib.sha256(Path(plan).read_bytes()).hexdigest()
    padj = part_adjacency(D)
    M = traffic(D)
    Ttab = CA.load(TABLE)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    maps = [(tag, load_regions(spec, D)) for tag, spec in maps_in]
    maps.append((f"v1_s{span:g}", propose(D, span, M, padj)))
    tlog = {}
    for s0, cap in tree_cfgs:
        reg, log = propose_tree(D, s0, cap, M, padj)
        tlog[f"tree_s{s0:g}c{cap:g}"] = log
        maps.append((f"tree_s{s0:g}c{cap:g}", reg))
    rows, keep = [], {}
    for name, reg in maps:
        (out / f"{die}_{name}_regions.json").write_text(json.dumps(dict(part_region=reg), indent=0, sort_keys=True))
        for feed in feeds:
            S = score(D, reg, v, feed, padj, M, Ttab)
            S["_reg"] = reg
            s = S["summary"]
            s["map"] = name
            rows.append(s)
            keep[(name, feed)] = S
            with gzip.open(out / f"{die}_{name}_{feed}_v2_crossings.json.gz", "wt") as fh:
                json.dump(S["crossings"], fh)
            print(die, name, feed, {k: s.get(k) for k in ("regions", "crossing_ports", "off_feed_ports",
                                                          "raw_worst_tt", "raw_worst_ff", "ca_worst_tt", "ca_worst_ff")},
                  flush=True)
    best = {}
    for mode, key, _ in MODES:
        cand = [r for r in rows if r.get(f"{key}_worst_tt") is not None]
        def rank(r):  # passing forms first, then (hop modes) the fewest extra landing cycles, else the best margin
            m = min(r[f"{key}_worst_tt"], r[f"{key}_worst_ff"])
            cost = r.get("hop_extra_bit_hops", 0) if key.startswith("hop_") else 0
            return (m >= 100.0, -cost if m >= 100.0 else m, m, -(r[f"{key}_under100_tt"] + r[f"{key}_under100_ff"]))
        b = max(cand, key=rank)
        S = keep[(b["map"], b["feed"])]
        png = f"{die}_v2_best_{mode}.png"
        if render_png:
            render(D, S, out / png, f"{die} best {mode}: map {b['map']} feed {b['feed']}", key)
        best[mode] = dict(map=b["map"], feed=b["feed"], tt=b[f"{key}_worst_tt"], ff=b[f"{key}_worst_ff"],
                          under100_tt=b[f"{key}_under100_tt"], under100_ff=b[f"{key}_under100_ff"],
                          passes=min(b[f"{key}_worst_tt"], b[f"{key}_worst_ff"]) >= 100.0, png=png,
                          worst=sorted(key_rows(S, key)[0], key=lambda r: min(r[f"{key_rows(S, key)[1]}_tt"],
                                                                         r[f"{key_rows(S, key)[1]}_ff"]))[:8],
                          rk=key_rows(S, key)[1], hop=dict(chains=b.get("hop_chains"), max_hops=b.get("hop_max_hops"),
                                                           extra_bit_hops=b.get("hop_extra_bit_hops")))
    res = dict(die=die, plan=dict(path=str(plan), sha256=D["_sha"]), v_ps_per_mm=v, rows=rows, best=best,
               tree_log={k: lg[:1] + lg[-1:] for k, lg in tlog.items()}, calib=calib)
    (out / f"{die}_v2.json").write_text(json.dumps(res, indent=0, default=str))
    (out / f"{die}_v2_ESTIMATE.md").write_text(estimate_md_v2(die, v, rows, best, D, res["tree_log"], calib))
    return res


def estimate_md_v2(die, v, rows, best, D, tlog, calib=None):
    L = [f"# 12.14b ESTIMATE v2: {die} region map / clock feed / crossings (LOCALITY-SCORE-2, analytic, UNCHECKED)", "",
         f"Inputs: plan {D['_plan']} (sha256 {D['_sha'][:12]}), {len(D['parts'])} partitions, {len(D['ports'])} ports; "
         f"v = {v:g} ps/mm TT; P = {D['period']:g} ps, budget P/2 = {D['period'] / 2:g} ps.",
         "Feeds: fwd = neighbour-forwarded from a parent LEAF (H-tree regions); spine = one spine along the max-bit "
         "spanning tree of the region adjacency (through every region centre; H-tree region trees hang off it); "
         "fish = the same spine + fishbone region trees (long-axis spine + ribs, leaf delay = Manhattan distance); "
         "dme = the spine made zero-skew (DME pads at the spine nodes: nominal d = 0, unshared = height of the last common "
         "spine node; LAND-HEAD-3's balanced spine form); top = one balanced die H-tree. Maps: given, v1 = connectivity greedy (span cap), tree_sXcY = proposer v2 "
         "(start span X mm, crossing graph made a tree by merge/re-cut up to cap Y mm).",
         "Modes: CURRENT RING = landed_phase_ocv margin with the nominal d (phase-dependent); COUNT-ALIGNED = budget - "
         "max(p_up, p_dn), nominal d absorbed by the ring count (ASSUMED definition = LAND-HEAD-3's reading, pending the "
         "MESO-COUNT-1 window verdict; it re-centres d per corner, i.e. it ASSUMES the ring count is trained at reset at "
         "the operating PVT); STATIC COUNT = one whole-cycle k per crossing for TT and FF (= FOLD: the corner-to-corner "
         "shift of d stays in the window). Derate: clk_aocv g021 + droop regions + core latency class B (shared model).",
         ""]
    if calib:
        L += ["Calibration: " + calib, ""]
    L += ["| mode | best map | feed | worst TT / FF ps | <100 TT / FF | >=100 TT and FF |", "|---|---|---|---|---|---|"]
    L[-2:-2] = ["Hop modes (12.13c): every off-feed crossing (loop-closing or far) is re-timed as a hop chain along the "
                "feed-tree path, one fixed-latency landing per tree edge; only feed parent<->child crossings remain. "
                "Cost = extra landing cycles (bit-hops), reported per map.", ""]
    for mode, key, desc in MODES:
        b = best[mode]
        L.append(f"| {mode} | {b['map']} | {b['feed']} | {b['tt']:.0f} / {b['ff']:.0f} | {b['under100_tt']} / "
                 f"{b['under100_ff']} | {'YES' if b['passes'] else 'no'} |")
    L += ["", "| map | feed | regions | max span mm | bit-mm inside | crossing ports | off-feed (loop) ports / pairs | "
          "worst unshared ns (on / off feed) | max tree hops | CURRENT RING TT/FF (<100) | COUNT-ALIGNED TT/FF (<100) | "
          "hop chains: n / max hops / extra bit-hops | RING+HOP TT/FF (<100) | CA+HOP TT/FF (<100) |",
          "|" + "---|" * 14]
    for s in rows:
        L.append(f"| {s['map']} | {s['feed']} | {s['regions']} | {s['max_span_mm']:.2f} | "
                 f"{100 * (s['frac_bitmm_inside'] or 0):.1f} % | {s['crossing_ports']} | {s['off_feed_ports']} / "
                 f"{s['loop_pairs']} | {s['worst_unshared_on_feed_tt'] / 1000:.2f} / "
                 f"{s['worst_unshared_off_feed_tt'] / 1000:.2f} | {s['max_tree_hops']} | "
                 f"{s['raw_worst_tt']:.0f} / {s['raw_worst_ff']:.0f} ({s['raw_under100_tt']}/{s['raw_under100_ff']}) | "
                 f"{s['ca_worst_tt']:.0f} / {s['ca_worst_ff']:.0f} ({s['ca_under100_tt']}/{s['ca_under100_ff']}) | "
                 + ("- | - | - |" if s.get("hop_ca_worst_tt") is None else
                    f"{s['hop_chains']} / {s['hop_max_hops']} / {s['hop_extra_bit_hops']} | "
                    f"{s['hop_raw_worst_tt']:.0f} / {s['hop_raw_worst_ff']:.0f} "
                    f"({s['hop_raw_under100_tt']}/{s['hop_raw_under100_ff']}) | "
                    f"{s['hop_ca_worst_tt']:.0f} / {s['hop_ca_worst_ff']:.0f} "
                    f"({s['hop_ca_under100_tt']}/{s['hop_ca_under100_ff']}) |"))
    L.append("")
    for mode, key, desc in MODES:
        b = best[mode]
        L.append(f"Worst crossings, best {mode} ({b['map']} / {b['feed']}, {desc}): " + "; ".join(
            f"{r['ra']}->{r['rb']} {r['width']} b {'on' if r['on_feed'] else 'OFF'}-feed hops {r['tree_hops']}, "
            f"unshared {r['unshared_tt'] / 1000:.2f} ns, d {r['d_tt']:.0f}, p {r['p_tt']:.0f}/{r['p_ff']:.0f}, "
            f"margin {r[b['rk'] + '_tt']:.0f}/{r[b['rk'] + '_ff']:.0f}" for r in b["worst"][:5]))
        if key.startswith("hop_"):
            L.append(f"  Hop cost: {b['hop']['chains']} off-feed crossings become chains, max {b['hop']['max_hops']} "
                     f"tree hops, {b['hop']['extra_bit_hops']} extra bit-hops (each extra hop = one more landing "
                     f"cycle on that path; price it in the die's token model)")
        L.append(f"  Render: {b['png']}")
    L += ["", "Tree proposer log (start -> end: loop-closing bits, loop pairs, regions): " + "; ".join(
        f"{k}: {lg[0][1]} b/{lg[0][2]} p/{lg[0][3]} r -> {lg[-1][1]} b/{lg[-1][2]} p/{lg[-1][3]} r"
        for k, lg in tlog.items()), "",
        "Verdict rule (12.14b): build only a map/feed whose estimated margin is >= 100 ps TT and FF on every crossing in "
        "the ring mode that will be built. Every number here is an ESTIMATE (UNCHECKED) until a GRT + landed_phase_ocv "
        "run."]
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------------------------------------------- CLI
def run(plan, regions, die, v, out, tag, feeds=("fwd", "spt", "top"), propose_span=None, render_png=True):
    import hashlib
    D = load_plan(plan)
    D["_plan"] = str(plan)
    D["_sha"] = hashlib.sha256(Path(plan).read_bytes()).hexdigest()
    padj = part_adjacency(D)
    M = traffic(D)
    Ttab = CA.load(TABLE)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    maps = []
    if regions:
        maps.append((tag or "baseline", load_regions(regions, D)))
    if propose_span:
        maps.append((f"proposed_s{propose_span:g}", propose(D, propose_span, M, padj)))
    runs = []
    for name, reg in maps:
        (out / f"{die}_{name}_regions.json").write_text(json.dumps(dict(part_region=reg), indent=0, sort_keys=True))
        for feed in feeds:
            S = score(D, reg, v, feed, padj, M, Ttab)
            S["_reg"] = reg
            keep = {k: S[k] for k in ("summary", "regions", "feed", "tracks")}
            rows = sorted(S["crossings_pad"] or S["crossings"], key=lambda r: min(r["fold_tt"], r["fold_ff"]))
            keep["crossings_worst100"] = rows[:100]
            keep["plan"] = dict(path=str(plan), sha256=D["_sha"])
            (out / f"{die}_{name}_{feed}.json").write_text(json.dumps(keep, indent=0))
            with gzip.open(out / f"{die}_{name}_{feed}_crossings.json.gz", "wt") as fh:
                json.dump(dict(nopad=S["crossings"], pad=S["crossings_pad"]), fh)
            if render_png:
                render(D, S, out / f"{die}_{name}_{feed}.png", f"{die} {name} feed={feed}")
            runs.append((f"{name}", S))
            print(die, name, feed, json.dumps(S["summary"]))
    (out / f"{die}_traffic.json").write_text(json.dumps(
        dict(top_pairs=[dict(a=a, b=b, **m) for (a, b), m in sorted(M.items(), key=lambda kv: -kv[1]["bitmm"])[:200]],
             pairs=len(M), bits=sum(m["bits"] for m in M.values()),
             bitmm=round(sum(m["bitmm"] for m in M.values()), 1)), indent=0))
    (out / f"{die}_ESTIMATE.md").write_text(estimate_md(die, v, runs, D))
    return runs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("score", "propose", "both", "v2"))
    ap.add_argument("--plan", required=True)
    ap.add_argument("--regions", help="region map JSON or 'part'")
    ap.add_argument("--tag", default="baseline")
    ap.add_argument("--die", required=True)
    ap.add_argument("--v-ps-mm", type=float, required=True, help="measured TT clock trunk delay per mm")
    ap.add_argument("--span-mm", type=float, default=3.5)
    ap.add_argument("--feed", default="fwd,spt,top")
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-png", action="store_true")
    ap.add_argument("--map", action="append", default=[], help="v2: TAG=MAP (repeatable; MAP = JSON or 'part')")
    ap.add_argument("--tree", default="2:3.5,3.5:5", help="v2: tree proposer start-span:cap list (mm)")
    ap.add_argument("--calib", default=None, help="v2: calibration note for the ESTIMATE page")
    a = ap.parse_args(argv)
    if a.cmd == "v2":
        cfg = tuple(tuple(float(t) for t in c.split(":")) for c in a.tree.split(",") if c)
        feeds = tuple(a.feed.split(",")) if a.feed != "fwd,spt,top" else ("fwd", "spine", "fish", "dme", "top")
        run_v2(a.plan, a.die, a.v_ps_mm, a.out, [tuple(m.split("=", 1)) for m in a.map], cfg, a.span_mm, feeds,
               not a.no_png, a.calib)
        return 0
    regions = a.regions if a.cmd in ("score", "both") else None
    span = a.span_mm if a.cmd in ("propose", "both") else None
    run(a.plan, regions, a.die, a.v_ps_mm, a.out, a.tag, tuple(a.feed.split(",")), span, not a.no_png)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
