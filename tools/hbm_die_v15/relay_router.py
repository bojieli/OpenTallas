#!/usr/bin/env python3
"""Obstacle-aware relay station planning (H-DIE 2026-10-16 18:40, d4b-r).

Why: d4b station points followed x-then-y L routes straight through hard macros. 20,134 of 34,847 relay homes
fell inside SU/SM/HC/SVG/PHY outlines, die_case legalised them up to 4.1 mm away, and 14,928 edges / 5.07 Mb
ended over 500 um (corrected GEN 1552, postprocess reach.json).

Model (geometry only, die-level wires may pass OVER a macro on the upper layers, a station tile may not sit IN one):
  * grid of G um cells over the die; a cell is FREE when no placed non-relay instance outline overlaps it;
  * a macro cell is PASSABLE when its taxicab distance to the nearest free cell <= R/2 - G (so a straight crossing
    is shorter than one reach); deeper macro cells are blocked;
  * each Prim-tree edge (same Manhattan Prim topology as die_relay_stations.tree) is routed by Dijkstra on the
    4-connected grid, cost G per free cell and 4 G per passable macro cell (prefer channels);
  * stations are placed greedily along the routed path: the farthest FREE cell that keeps the routed hop <= R.
    A hop that cannot meet R (no free cell within reach) is placed at the next free cell and reported as a
    violation with its routed length;
  * equal-age pads sit at the free cell nearest to their sink pin centroid.
Depths count routed hops, so they are >= the Manhattan depths of the old list. Hop = routed path length.
"""
import heapq, math
import numpy as np
from scipy import ndimage
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra


class Router:
    def __init__(self, placement, die_um, R, G=50.0, macro_cost=4.0, carved=None):
        self.R, self.G = float(R), float(G)
        W, H = die_um
        self.nx, self.ny = int(math.ceil(W / G)), int(math.ceil(H / G))
        occ = np.zeros((self.nx, self.ny), bool)
        carve = []
        for n, v in placement.items():
            if v.get('m', v.get('master', '')).startswith('hbfd_rly') or n.startswith('rly'):
                continue                               # relay tiles are not obstacles (they are what we place)
            for c in (carved or {}).get(v.get('m', v.get('master')), []):
                # die-owned feedthrough relay channel inside the master (die_case carved_feedthrough), local -> die
                (lx0, lx1), (ly0, ly1) = c['x_um'], c['y_um']
                o = v.get('o', v.get('orient', 'R0'))
                if o in ('MY', 'R180'):
                    lx0, lx1 = v['w'] - lx1, v['w'] - lx0
                if o in ('MX', 'R180'):
                    ly0, ly1 = v['h'] - ly1, v['h'] - ly0
                carve.append((v['x'] + lx0, v['y'] + ly0, v['x'] + lx1, v['y'] + ly1))
            w, h = v['w'], v['h']
            if v.get('o', v.get('orient', 'R0')) in ('R90', 'R270', 'MXR90', 'MYR90'):
                w, h = h, w
            x0, y0 = int(v['x'] // G), int(v['y'] // G)
            x1, y1 = int(math.ceil((v['x'] + w) / G)), int(math.ceil((v['y'] + h) / G))
            occ[max(0, x0):min(self.nx, x1), max(0, y0):min(self.ny, y1)] = True
        for x0, y0, x1, y1 in carve:                   # inner cells only: a station tile must fit in the channel
            cx0, cy0 = int(math.ceil(x0 / G)), int(math.ceil(y0 / G))
            cx1, cy1 = int(x1 // G), int(y1 // G)
            if cx1 > cx0 and cy1 > cy0:
                occ[cx0:cx1, cy0:cy1] = False
        self.carved_cells = len(carve)
        self.free = ~occ
        depth = ndimage.distance_transform_cdt(occ, metric='taxicab') * G
        self.passable = self.free | (depth <= R / 2 - G)
        idx = -np.ones((self.nx, self.ny), np.int64)
        pc = np.flatnonzero(self.passable.ravel())
        idx.ravel()[pc] = np.arange(len(pc))
        self.idx = idx
        self.cell = np.stack(np.unravel_index(pc, (self.nx, self.ny)), 1)
        cost = np.where(self.free.ravel()[pc], G, G * macro_cost)
        rows, cols, data = [], [], []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a = idx[max(0, -dx):self.nx - max(0, dx), max(0, -dy):self.ny - max(0, dy)]
            b = idx[max(0, dx):self.nx + min(0, dx), max(0, dy):self.ny + min(0, dy)]
            m = (a >= 0) & (b >= 0)
            rows.append(a[m]); cols.append(b[m]); data.append(cost[b[m]])
        n = len(pc)
        self.graph = csr_matrix((np.concatenate(data), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n))
        fr = np.argwhere(self.free)
        self._free_cells = fr

    def node(self, p):
        """passable grid node nearest to point p (snap = Manhattan um added to the path)"""
        cx, cy = min(self.nx - 1, max(0, int(p[0] // self.G))), min(self.ny - 1, max(0, int(p[1] // self.G)))
        if self.idx[cx, cy] >= 0:
            return int(self.idx[cx, cy]), 0.0
        for r in range(1, max(self.nx, self.ny)):
            best = None
            for dx in range(-r, r + 1):
                for dy in (r - abs(dx), -(r - abs(dx))):
                    x, y = cx + dx, cy + dy
                    if 0 <= x < self.nx and 0 <= y < self.ny and self.idx[x, y] >= 0:
                        best = (int(self.idx[x, y]), r * self.G)
                        break
                if best:
                    return best
        raise ValueError(f'no passable cell near {p}')

    def nearest_free(self, p):
        cx, cy = int(p[0] // self.G), int(p[1] // self.G)
        d = np.abs(self._free_cells[:, 0] - cx) + np.abs(self._free_cells[:, 1] - cy)
        x, y = self._free_cells[int(np.argmin(d))]
        return ((x + 0.5) * self.G, (y + 0.5) * self.G)

    def _xy(self, k):
        return divmod(-1 - k, self.ny) if k < 0 else tuple(self.cell[k])

    def centre(self, k):
        x, y = self._xy(k)
        return ((x + 0.5) * self.G, (y + 0.5) * self.G)

    def is_free(self, k):
        x, y = self._xy(k)
        return bool(self.free[x, y])

    def route(self, a, b):
        """routed node path a->b (list of node ids)"""
        s, _ = self.node(a); t, _ = self.node(b)
        if s == t:
            return [s]
        lim = 4 * (abs(a[0] - b[0]) + abs(a[1] - b[1])) + 20 * self.R
        dist, pred = dijkstra(self.graph, indices=s, return_predecessors=True, limit=lim)
        if not np.isfinite(dist[t]):
            dist, pred = dijkstra(self.graph, indices=s, return_predecessors=True)
            if not np.isfinite(dist[t]):
                return self.route_full(a, b)
        path = [t]
        while path[-1] != s:
            path.append(int(pred[path[-1]]))
        return path[::-1]


    def route_full(self, a, b):
        """Fallback when a and b are not connected through free/passable cells (a sealed region): route on the
        full grid, blocked macro cells at 20x cost.  Returns nodes of the passable graph where possible; the hops
        that cross blocked cells come out as violations (a floorplan defect to fix, never hidden)."""
        if not hasattr(self, '_full'):
            n = self.nx * self.ny
            ids = np.arange(n).reshape(self.nx, self.ny)
            cost = np.where(self.free, self.G, np.where(self.passable, self.G * 4, self.G * 20)).ravel()
            rows, cols, data = [], [], []
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                a_ = ids[max(0, -dx):self.nx - max(0, dx), max(0, -dy):self.ny - max(0, dy)].ravel()
                b_ = ids[max(0, dx):self.nx + min(0, dx), max(0, dy):self.ny + min(0, dy)].ravel()
                rows.append(a_); cols.append(b_); data.append(cost[b_])
            self._full = csr_matrix((np.concatenate(data), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n))
        cx = lambda p: min(self.nx - 1, max(0, int(p[0] // self.G))) * self.ny + min(self.ny - 1, max(0, int(p[1] // self.G)))
        s, t = cx(a), cx(b)
        _, pred = dijkstra(self._full, indices=s, return_predecessors=True)
        path = [t]
        while path[-1] != s:
            path.append(int(pred[path[-1]]))
        path = path[::-1]
        out = []
        for k in path:                                 # encode non-passable cells as negative ids (-1 - flat index)
            x, y = divmod(k, self.ny)
            out.append(int(self.idx[x, y]) if self.idx[x, y] >= 0 else -1 - k)
        return out


def flow(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    if abs(dx) >= abs(dy):
        return 'WE' if dx >= 0 else 'EW'
    return 'SN' if dy >= 0 else 'NS'


def plan_bus(router, P, par, R, W, sinks):
    """Routed station tree.  P/par = Prim tree (P[0] = driver centroid, P[i] = sink i-1 centroid).
    Returns (stations[id,depth,x,y,toward,master,parent,pt,hop_um], tail{node: last station id or None},
    depth per sink, violations[(hop_um, where)])."""
    G = router.G
    kids = {}
    for v in range(1, len(P)):
        kids.setdefault(par[v], []).append(v)
    order, q = [], [0]
    while q:
        u = q.pop(0)
        for v in kids.get(u, []):
            order.append(v); q.append(v)
    sl, viol = [], []
    # state at a tree node: (last station id, routed um since it, depth, point of last station)
    state = {0: (None, 0.0, 0, P[0])}
    for v in order:
        u = par[v]
        prev, run, dep, ppt = state[u]
        path = router.route(P[u], P[v])
        _, snap_a = router.node(P[u]); _, snap_b = router.node(P[v])
        run += snap_a
        cand = None                                  # (index in path, run at that cell) of last free cell
        i = 1 if len(path) > 1 else 0
        while i < len(path):
            run += G
            if run > R:
                if cand is not None:
                    ci, crun = cand
                    k = path[ci]; pt = router.centre(k)
                    sl.append(dict(id=len(sl), depth=dep + 1, x=round(pt[0], 1), y=round(pt[1], 1), toward=None,
                                   master=f'hbfd_rly_{W}_{flow(ppt, pt)}', parent=prev, pt=pt, hop_um=round(crun, 1)))
                    prev, dep, ppt = sl[-1]['id'], dep + 1, pt
                    run = (i - ci) * G
                    cand = None
                    if router.is_free(path[i]):
                        cand = (i, run)
                    i += 1
                    continue
                # no free cell within reach: take the next free cell, report the hop
                j = i
                while j < len(path) and not router.is_free(path[j]):
                    j += 1; run += G
                if j >= len(path):
                    viol.append((round(run, 1), f'toward sink {v - 1} (end of path)'))
                    break
                k = path[j]; pt = router.centre(k)
                viol.append((round(run, 1), f'station depth {dep + 1}'))
                sl.append(dict(id=len(sl), depth=dep + 1, x=round(pt[0], 1), y=round(pt[1], 1), toward=None,
                               master=f'hbfd_rly_{W}_{flow(ppt, pt)}', parent=prev, pt=pt, hop_um=round(run, 1)))
                prev, dep, ppt = sl[-1]['id'], dep + 1, pt
                run = 0.0; cand = None; i = j + 1
                continue
            if router.is_free(path[i]):
                cand = (i, run)
            i += 1
        run += snap_b
        if run > R + 1e-6:
            viol.append((round(run, 1), f'last hop into sink {v - 1}'))
        state[v] = (prev, run, dep, ppt)
    for s in sl:
        s['toward'] = None
    # toward: the first sink below each station (for the record)
    owner = {}
    for v in order:
        sid = state[v][0]
        while sid is not None and sid not in owner:
            owner[sid] = sinks[v - 1]
            sid = sl[sid]['parent']
    for s in sl:
        s['toward'] = owner.get(s['id'], sinks[0])
    tail = {v: state[v][0] for v in state}
    depth = [state[v][2] for v in range(1, len(P))]
    return sl, tail, depth, viol
