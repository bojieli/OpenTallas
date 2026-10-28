"""Region grouping: macros + glue -> K partitions under a cell cap.

Method (deliberately simple and deterministic):
1. Frontier: an instance subtree is one atomic *item* if it has at most
   ``unit_max_cells`` leaf cells; larger subtrees are opened and their
   children / direct glue cells become items.  Logical hierarchy is kept
   where it is small enough, as industry partitioning does.
2. Item graph: clique-weighted (1/(d-1)) connectivity of every signal net of
   degree <= ``max_net_degree``; clock nets and very high fanout nets are
   left out of the cost (they are counted in the cut report).
3. Agglomerative clustering (best score = w_ab / (s_a * s_b)) under a hard
   cell cap and an area-balance ceiling, down to K clusters.
4. FM-style refinement: single-item moves with positive cut gain that keep
   the cap and balance.
5. Slicing floorplan: recursive bisection of the cluster order (min cut
   between halves, area-proportional cut, both cut directions tried, hard
   macro fit checked), giving one rectangle per partition.
"""
from __future__ import annotations

import heapq
import math
from collections import defaultdict


# ---------------------------------------------------------------- frontier
def build_items(nl, libcells, unit_max_cells, leaf_group=None):
    """Return (items, leaf_item) where items = [dict(name, leaves, cells, area, macros)].

    leaf_group (optional, region-map mode): leaf index -> group or None.  A subtree is
    only kept whole if all its mapped leaves are in one group, so no item straddles
    a region of the map."""
    items = []
    leaf_item = [None] * len(nl.leaves)

    def uniform(node):
        if leaf_group is None:
            return True
        lv = []
        collect(node, lv)
        return len({leaf_group[li] for li in lv} - {None}) <= 1

    def collect(node, out):
        out.extend(node.leaves)
        for ch in node.children:
            collect(ch, out)

    def visit(node):
        if node.path and node.n_cells <= unit_max_cells and uniform(node):
            lv = []
            collect(node, lv)
            _add_item(".".join(node.path), lv)
            return
        for li in node.leaves:
            _add_item(nl.leaves[li].name, [li])
        for ch in node.children:
            visit(ch)

    def _add_item(name, lv):
        idx = len(items)
        area = mac_area = 0.0
        macros = []
        for li in lv:
            leaf_item[li] = idx
            c = libcells.get(nl.leaves[li].type)
            if c is None:
                continue
            if c.is_macro:
                mac_area += c.area
                macros.append(li)
            else:
                area += c.area
        items.append({"name": name, "leaves": lv, "cells": len(lv), "area": area,
                      "macro_area": mac_area, "macros": macros})

    visit(nl.tree)
    return items, leaf_item


def item_graph(nl, leaf_item, clock_nets, max_net_degree):
    """Return adjacency {a: {b: w}} and per-net item sets (all nets)."""
    pins = nl.net_pins()
    adj = defaultdict(lambda: defaultdict(float))
    net_items = {}
    for net, pl in pins.items():
        s = sorted({leaf_item[li] for li, _, _ in pl})
        net_items[net] = s
        if len(s) < 2 or net in clock_nets or len(pl) > max_net_degree:
            continue
        w = 1.0 / (len(s) - 1)
        if len(s) > 16:      # avoid O(d^2) on wide nets: star to the first item
            for b in s[1:]:
                adj[s[0]][b] += w
                adj[b][s[0]] += w
            continue
        for i, a in enumerate(s):
            for b in s[i + 1:]:
                adj[a][b] += w
                adj[b][a] += w
    return adj, net_items


def assign_from_map(items, adj, leaf_group, k):
    """Region-map mode: every item goes to the region its leaves are mapped to;
    unmapped glue follows its strongest connection (clock follows data, glue follows
    its neighbours), repeated until stable; leftovers (no mapped neighbour) go to the
    smallest region.  -> (assign, n_glue)"""
    assign = [None] * len(items)
    for i, it in enumerate(items):
        g = {leaf_group[li] for li in it["leaves"]} - {None}
        if len(g) > 1:
            raise ValueError(f"item {it['name']} straddles regions {sorted(g)}")
        if g:
            assign[i] = g.pop()
    glue = [i for i, a in enumerate(assign) if a is None]
    changed = True
    while changed:
        changed = False
        for i in glue:
            if assign[i] is not None:
                continue
            conn = defaultdict(float)
            for j, w in adj.get(i, {}).items():
                if assign[j] is not None:
                    conn[assign[j]] += w
            if conn:
                assign[i] = max(sorted(conn), key=lambda q: conn[q])
                changed = True
    cells = [0] * k
    for i, a in enumerate(assign):
        if a is not None:
            cells[a] += items[i]["cells"]
    for i in glue:
        if assign[i] is None:
            q = min(range(k), key=lambda q: cells[q])
            assign[i] = q
            cells[q] += items[i]["cells"]
    return assign, len(glue)


# ---------------------------------------------------------------- clustering
def cluster(items, adj, k, cap_cells, balance_eps=0.3, macro_weight=1.0):
    n = len(items)
    total_area = sum(it["area"] + macro_weight * it["macro_area"] for it in items) or 1.0
    area_ceiling = (1.0 + balance_eps) * total_area / k
    if sum(it["cells"] for it in items) > k * cap_cells:
        raise ValueError(f"{sum(it['cells'] for it in items)} cells cannot fit in {k} x {cap_cells}")
    parent = list(range(n))
    cells = [it["cells"] for it in items]
    area = [it["area"] + macro_weight * it["macro_area"] for it in items]
    members = {i: [i] for i in range(n)}
    cadj = {i: dict(adj.get(i, {})) for i in range(n)}
    alive = set(range(n))
    ver = [0] * n
    heap = []

    def score(a, b, w):
        return w / (max(area[a], 1e-3) * max(area[b], 1e-3))

    def ok(a, b):
        return cells[a] + cells[b] <= cap_cells and area[a] + area[b] <= area_ceiling

    for a in range(n):
        for b, w in cadj[a].items():
            if a < b:
                heapq.heappush(heap, (-score(a, b, w), a, b, 0, 0))

    def merge(a, b):
        if len(cadj[a]) < len(cadj[b]):
            a, b = b, a
        for c, w in cadj[b].items():
            if c == a:
                continue
            cadj[a][c] = cadj[a].get(c, 0.0) + w
            cadj[c][a] = cadj[a][c]
            cadj[c].pop(b, None)
        cadj[a].pop(b, None)
        cadj[b] = {}
        cells[a] += cells[b]
        area[a] += area[b]
        members[a].extend(members.pop(b))
        alive.discard(b)
        ver[a] += 1
        ver[b] += 1
        for c, w in cadj[a].items():
            x, y = (a, c) if a < c else (c, a)
            heapq.heappush(heap, (-score(x, y, w), x, y, ver[x], ver[y]))
        return a

    while len(alive) > k and heap:
        s, a, b, va, vb = heapq.heappop(heap)
        if a not in alive or b not in alive or va != ver[a] or vb != ver[b]:
            continue
        if not ok(a, b):
            continue
        merge(a, b)
    # disconnected leftovers / blocked merges: smallest-into-smallest that fits
    while len(alive) > k:
        order = sorted(alive, key=lambda c: area[c])
        a = order[0]
        tgt = next((b for b in order[1:] if cells[a] + cells[b] <= cap_cells), None)
        if tgt is None:
            raise ValueError("cannot reach K clusters under the cell cap")
        merge(tgt, a)
    assign = [None] * n
    for ci, c in enumerate(sorted(alive, key=lambda c: -area[c])):
        for i in members[c]:
            assign[i] = ci
    return assign


def refine(items, adj, assign, k, cap_cells, balance_eps=0.3, passes=8, macro_weight=1.0):
    area = [0.0] * k
    cells = [0] * k
    for i, p in enumerate(assign):
        area[p] += items[i]["area"] + macro_weight * items[i]["macro_area"]
        cells[p] += items[i]["cells"]
    ceiling = (1.0 + balance_eps) * sum(area) / k
    moved_total = 0
    for _ in range(passes):
        moved = 0
        for i in range(len(items)):
            nb = adj.get(i)
            if not nb:
                continue
            p = assign[i]
            conn = defaultdict(float)
            for j, w in nb.items():
                conn[assign[j]] += w
            best, gain = p, 0.0
            a_i = items[i]["area"] + macro_weight * items[i]["macro_area"]
            for q, w in conn.items():
                if q == p:
                    continue
                g = w - conn.get(p, 0.0)
                if g > gain + 1e-9 and area[q] + a_i <= ceiling and \
                        cells[q] + items[i]["cells"] <= cap_cells and cells[p] > items[i]["cells"]:
                    best, gain = q, g
            if best != p:
                assign[i] = best
                area[p] -= a_i
                area[best] += a_i
                cells[p] -= items[i]["cells"]
                cells[best] += items[i]["cells"]
                moved += 1
        moved_total += moved
        if not moved:
            break
    return assign, moved_total


def cut_report(nl, leaf_item, assign, k, clock_nets):
    """Crossing bits per partition pair, per partition port counts."""
    pins = nl.net_pins()
    pnets = nl.port_nets()
    pair = defaultdict(int)
    ports = [0] * k
    crossing = 0
    for net, pl in pins.items():
        parts = {assign[leaf_item[li]] for li, _, _ in pl}
        if net in pnets:
            parts.add("IO")
        real = sorted(p for p in parts if p != "IO")
        if len(parts) > 1:
            for p in real:
                ports[p] += 1
        if len(real) > 1 and net not in clock_nets:
            crossing += 1
            for i, a in enumerate(real):
                for b in real[i + 1:]:
                    pair[(a, b)] += 1
    return {"crossing_bits": crossing, "pairs": {f"{a}-{b}": v for (a, b), v in sorted(pair.items())},
            "ports_per_partition": ports}


# ---------------------------------------------------------------- floorplan
def shelf_fit(dims, rect, channel=0.0, halo=0.0, allow_rotate=False):
    """Shelf-pack macros (w, h) with halos into the rectangle minus the channel."""
    x0, y0, x1, y1 = rect
    rw, rh = x1 - x0 - channel, y1 - y0 - channel
    dims = sorted(dims, key=lambda d: -d[1])
    for orient in ((False, True) if allow_rotate else (False,)):
        ds = [((h, w) if orient else (w, h)) for w, h in dims]
        ds.sort(key=lambda d: -d[1])
        shelf_y, shelf_h, cur_x, ok = 0.0, 0.0, 0.0, True
        for w, h in ds:
            w2, h2 = w + 2 * halo, h + 2 * halo
            if w2 > rw:
                ok = False
                break
            if cur_x + w2 > rw:          # next shelf
                shelf_y += shelf_h
                cur_x, shelf_h = 0.0, 0.0
            cur_x += w2
            shelf_h = max(shelf_h, h2)
            if shelf_y + shelf_h > rh:
                ok = False
                break
        if ok:
            return True
    return not dims


def floorplan(parts, conn, die_w, die_h, channel=2.0, halo=2.0, allow_rotate=False):
    """parts: [{id, area_um2, macro_dims:[(w,h)]}]; conn[(a,b)] = bits.

    Returns {id: (x0, y0, x1, y1)} using recursive slicing bisection.
    """
    ids = [p["id"] for p in parts]
    by_id = {p["id"]: p for p in parts}

    def w(a, b):
        return conn.get((min(a, b), max(a, b)), 0)

    # greedy linear order: start at the most-connected partition
    order = [max(ids, key=lambda a: sum(w(a, b) for b in ids if b != a))] if ids else []
    rest = set(ids) - set(order)
    while rest:
        nxt = max(sorted(rest), key=lambda b: sum(w(a, b) * (0.5 ** (len(order) - 1 - i))
                                                   for i, a in enumerate(order)))
        order.append(nxt)
        rest.discard(nxt)

    def fits(pid, rect):
        return shelf_fit(by_id[pid]["macro_dims"], rect, channel, halo, allow_rotate)

    def aspect_pen(rect):
        x0, y0, x1, y1 = rect
        a = abs(math.log((x1 - x0) / max(y1 - y0, 1e-6)))
        # beyond 2:1 a partition gets few rows / one-sided pins (measured: a 20x10 um,
        # 7.6 um-core slot failed detailed placement in ORFS): steep extra penalty
        return a + 4.0 * max(0.0, a - math.log(2.0))

    def solve(seq, rect):
        """Return (penalty, {id: rect}) for this subsequence."""
        if len(seq) == 1:
            pid = seq[0]
            pen = 2.0 * aspect_pen(rect) ** 2 + (0 if fits(pid, rect) else 1e6)
            return pen, {pid: rect}
        best = None
        tot = sum(by_id[p]["area_um2"] for p in seq)
        cuts = range(1, len(seq))
        if len(seq) > 8:   # keep the search polynomial: only the balanced cut
            acc, cuts = 0.0, []
            for i, p in enumerate(seq[:-1]):
                acc += by_id[p]["area_um2"]
                cuts.append((abs(acc / tot - 0.5), i + 1))
            cuts = [min(cuts)[1]]
        for cut in cuts:
            L, R = seq[:cut], seq[cut:]
            aL = sum(by_id[p]["area_um2"] for p in L) / tot
            cutw = sum(w(a, b) for a in L for b in R)
            for vertical in (True, False):
                x0, y0, x1, y1 = rect
                if vertical:
                    xm = x0 + (x1 - x0) * aL
                    r1, r2 = (x0, y0, xm, y1), (xm, y0, x1, y1)
                else:
                    ym = y0 + (y1 - y0) * aL
                    r1, r2 = (x0, y0, x1, ym), (x0, ym, x1, y1)
                p1, m1 = solve(L, r1)
                p2, m2 = solve(R, r2)
                pen = p1 + p2 + 1e-3 * cutw + 0.2 * abs(aL - 0.5)
                if best is None or pen < best[0]:
                    best = (pen, {**m1, **m2})
        return best

    pen, rects = solve(order, (0.0, 0.0, die_w, die_h))
    out = {}
    for pid, (x0, y0, x1, y1) in rects.items():
        h = channel / 2
        out[pid] = (round(x0 + h, 3), round(y0 + h, 3), round(x1 - h, 3), round(y1 - h, 3))
    return out, pen < 1e6
