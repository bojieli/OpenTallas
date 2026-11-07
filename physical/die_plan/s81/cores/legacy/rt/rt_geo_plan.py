#!/usr/bin/env python3
"""S81-ENGRR-B7 11-07: macro-aware regional clock spine plan (OT_RT_GEO=1, regional_taps_geo.tcl).

Why: the geometric H-tree of regional_taps.tcl puts nodes inside macro stacks; legalized repeaters then double back
(eng_rr_e vG: ~700 um and 4 hops of 82-115 ps to reach sinks 100 um from the trunk, 120 ps routed tap error).
This plan: taps come from the placed sinks (clusters limited by count, span and walking distance around macros), the
spine runs on shortest paths through free channels from one hub, with a repeater at least every OT_RT_REP_UM.

Input TSV  (argv[1]):  CORE x0 y0 x1 y1 | PORT x y | MACRO x0 y0 x1 y1 | MTAP name x y | REG name x y
Output TSV (argv[2]):  BUF id x y parent | TAP name x y parent | ASSIGN regname tapname ; parent = ROOT or BUF id
Deterministic: no randomness, ties broken by coordinates/names.
"""
import os
import sys
from collections import deque


def env(k, d):
    return float(os.environ.get(k, d))


GRID = env("OT_RTG_GRID_UM", 2.0)
REP = env("OT_RT_REP_UM", 80.0)
CMAX = int(env("OT_RTG_CMAX", 900))
SPAN = env("OT_RTG_SPAN_UM", 110.0)
GEOMAX = env("OT_RTG_WALK_UM", 130.0)
HALO = env("OT_RTG_HALO_UM", 4.6)  # buffers stay outside this; wires may walk up to the macro edge
CMIN = int(env("OT_RTG_CMIN", 40))


class Grid:
    def __init__(self, core, macros):
        self.x0, self.y0, self.x1, self.y1 = core
        self.nx = int((self.x1 - self.x0) / GRID) + 1
        self.ny = int((self.y1 - self.y0) / GRID) + 1
        self.free = bytearray(b"\1" * (self.nx * self.ny))    # a wire can walk here
        self.bufok = bytearray(b"\1" * (self.nx * self.ny))   # a repeater can land here
        for mx0, my0, mx1, my1 in macros:
            for j in range(self.ny):
                y = self.y0 + j * GRID
                if not (my0 - HALO <= y <= my1 + HALO):
                    continue
                for i in range(self.nx):
                    x = self.x0 + i * GRID
                    if mx0 - HALO <= x <= mx1 + HALO:
                        self.bufok[j * self.nx + i] = 0
                        if mx0 <= x <= mx1 and my0 <= y <= my1:
                            self.free[j * self.nx + i] = 0

    def cell(self, x, y):
        i = min(max(int(round((x - self.x0) / GRID)), 0), self.nx - 1)
        j = min(max(int(round((y - self.y0) / GRID)), 0), self.ny - 1)
        return j * self.nx + i

    def xy(self, c):
        return (self.x0 + (c % self.nx) * GRID, self.y0 + (c // self.nx) * GRID)

    def nbrs(self, c):
        i, j = c % self.nx, c // self.nx
        if i + 1 < self.nx and self.free[c + 1]:
            yield c + 1
        if i > 0 and self.free[c - 1]:
            yield c - 1
        if j + 1 < self.ny and self.free[c + self.nx]:
            yield c + self.nx
        if j > 0 and self.free[c - self.nx]:
            yield c - self.nx

    def snap(self, x, y):
        """nearest free cell (Manhattan), deterministic"""
        c = self.cell(x, y)
        if self.free[c]:
            return c
        best, bd = None, 1e18
        for k in range(len(self.free)):
            if self.free[k]:
                a, b = self.xy(k)
                d = abs(a - x) + abs(b - y)
                if d < bd:
                    best, bd = k, d
        if best is None:
            raise SystemExit("OT_RTG: no free cell")
        return best

    def bfs(self, src):
        d = [-1] * len(self.free)
        d[src] = 0
        q = deque([src])
        while q:
            c = q.popleft()
            for n in self.nbrs(c):
                if d[n] < 0:
                    d[n] = d[c] + 1
                    q.append(n)
        return d


def median(v):
    v = sorted(v)
    return v[len(v) // 2]


def cluster(regs, grid):
    """regs = [(name,x,y)]; recursive 2-way split until count, span and walking distance are within limits"""
    work = [sorted(regs, key=lambda r: r[0])]
    done = []
    while work:
        c = work.pop()
        xs = [r[1] for r in c]
        ys = [r[2] for r in c]
        span = max(xs) - min(xs) + max(ys) - min(ys)
        tap = grid.snap(median(xs), median(ys))
        bad = len(c) > CMAX or span > SPAN
        if not bad:
            dist = grid.bfs(tap)
            for r in c:
                d = dist[grid.snap(r[1], r[2])] if not grid.free[grid.cell(r[1], r[2])] else dist[grid.cell(r[1], r[2])]
                if d < 0 or d * GRID > GEOMAX:
                    bad = True
                    break
        if not bad or len(c) < 2:
            done.append((c, tap))
            continue
        # farthest pair seeds (Manhattan), 4 Lloyd rounds
        a = max(c, key=lambda r: abs(r[1] - xs[0]) + abs(r[2] - ys[0]))
        b = max(c, key=lambda r: abs(r[1] - a[1]) + abs(r[2] - a[2]))
        sa, sb = (a[1], a[2]), (b[1], b[2])
        for _ in range(4):
            A = [r for r in c if abs(r[1] - sa[0]) + abs(r[2] - sa[1]) <= abs(r[1] - sb[0]) + abs(r[2] - sb[1])]
            B = [r for r in c if abs(r[1] - sa[0]) + abs(r[2] - sa[1]) > abs(r[1] - sb[0]) + abs(r[2] - sb[1])]
            if not A or not B:
                break
            sa = (median(r[1] for r in A), median(r[2] for r in A))
            sb = (median(r[1] for r in B), median(r[2] for r in B))
        if not A or not B:
            done.append((c, tap))
            continue
        work.append(A)
        work.append(B)
    # merge tiny clusters into the nearest cluster by walking distance
    done.sort(key=lambda t: (len(t[0]), t[0][0][0]))
    out = list(done)
    for item in done:
        if len(item[0]) >= CMIN or len(out) < 2:
            continue
        dist = grid.bfs(item[1])
        cands = [o for o in out if o is not item and 0 <= dist[o[1]] and dist[o[1]] * GRID <= GEOMAX + 40.0 and len(o[0]) + len(item[0]) <= CMAX]
        if not cands:
            continue
        o = min(cands, key=lambda o: (dist[o[1]], o[0][0][0]))
        o[0].extend(item[0])
        out = [x for x in out if x is not item]
    return sorted(out, key=lambda t: t[0][0][0])


def plan(core, port, macros, mtaps, regs):
    grid = Grid(core, macros)
    clusters = cluster(regs, grid) if regs else []
    taps = []  # (name, x, y, cell)
    for k, (c, cell) in enumerate(clusters):
        x, y = grid.xy(cell)
        taps.append(("ot_rt_t%d" % k, x, y, cell))
    for name, x, y in mtaps:
        taps.append((name, x, y, grid.snap(x, y)))
    # hub: free cell with the smallest worst walking distance to any tap
    dists = {}
    for t in taps:
        if t[3] not in dists:
            dists[t[3]] = grid.bfs(t[3])
    best, bv = None, 1e18
    for c in range(len(grid.free)):
        if not grid.bufok[c]:
            continue
        v = 0
        for d in dists.values():
            if d[c] < 0:
                v = 1e18
                break
            v = max(v, d[c])
        if v < bv:
            best, bv = c, v
    hub = best
    dh = grid.bfs(hub)
    # shortest-path tree from the hub, paths share cells whenever an equal-length step is already in the tree
    parent = {hub: None}
    pc = grid.cell(*port)
    if not grid.bufok[pc]:
        pc = grid.snap(*port)
    for t in sorted(taps, key=lambda t: -dh[t[3]]):
        c = t[3]
        if dh[c] < 0:
            raise SystemExit("OT_RTG: tap %s unreachable from hub" % t[0])
        prev_dir = None
        while c not in parent:
            cands = [n for n in grid.nbrs(c) if dh[n] == dh[c] - 1]
            intree = [n for n in cands if n in parent]
            if intree:
                n = min(intree)
            else:
                straight = [n for n in cands if prev_dir is not None and n - c == prev_dir]
                n = straight[0] if straight else min(cands)
            parent[c] = n
            prev_dir = n - c
            c = n
    children = {}
    for c, p in parent.items():
        if p is not None:
            children.setdefault(p, []).append(c)
    tap_at = {}
    for t in taps:
        tap_at.setdefault(t[3], []).append(t)
    rows = []
    nb = [0]

    def new_buf(c, par):
        nb[0] += 1
        x, y = grid.xy(c)
        rows.append(("BUF", nb[0], x, y, par))
        return nb[0]

    # port -> hub trunk
    drv = new_buf(pc, "ROOT")
    dp = grid.bfs(pc)
    path = [hub]
    while path[-1] != pc:
        n = min(n for n in grid.nbrs(path[-1]) if dp[n] == dp[path[-1]] - 1)
        path.append(n)
    acc = 0.0
    for c in reversed(path[:-1]):
        acc += GRID
        if (acc >= REP and grid.bufok[c]) or c == hub:
            drv = new_buf(c, drv)
            acc = 0.0
    # spine: iterative walk of the tree
    stack = [(hub, drv, 0.0)]
    maxacc = 0.0
    while stack:
        c, d, acc = stack.pop()
        maxacc = max(maxacc, acc)
        for t in tap_at.get(c, []):
            rows.append(("TAP", t[0], t[1], t[2], d))
        kids = sorted(children.get(c, []))
        if len(kids) >= 2 and acc > 16.0 and grid.bufok[c]:
            d = new_buf(c, d)
            acc = 0.0
        for k in kids:
            a2 = acc + GRID
            d2 = d
            if a2 >= REP and grid.bufok[k]:
                d2 = new_buf(k, d)
                a2 = 0.0
            stack.append((k, d2, a2))
    # tap points inside a macro halo are pulled out to the nearest repeater site by the caller's legalizer
    for (c, cell), t in zip(clusters, taps):
        for r in c:
            rows.append(("ASSIGN", r[0], t[0]))
    return rows, grid.xy(hub), bv * GRID, taps, clusters


def main():
    core = port = None
    macros, mtaps, regs = [], [], []
    for l in open(sys.argv[1]):
        p = l.rstrip("\n").split("\t")
        if p[0] == "CORE":
            core = tuple(map(float, p[1:5]))
        elif p[0] == "PORT":
            port = (float(p[1]), float(p[2]))
        elif p[0] == "MACRO":
            macros.append(tuple(map(float, p[1:5])))
        elif p[0] == "MTAP":
            mtaps.append((p[1], float(p[2]), float(p[3])))
        elif p[0] == "REG":
            regs.append((p[1], float(p[2]), float(p[3])))
    rows, hub, worst, taps, clusters = plan(core, port, macros, mtaps, regs)
    with open(sys.argv[2], "w") as f:
        for r in rows:
            f.write("\t".join(str(x) for x in r) + "\n")
    nbuf = sum(r[0] == "BUF" for r in rows)
    sizes = sorted(len(c[0]) for c in clusters)
    print("OT_RTG hub (%.1f,%.1f) worst walk %.0f um; %d region taps (sinks %d..%d), %d macro taps, %d spine buffers, rep %.0f um"
          % (hub[0], hub[1], worst, len(clusters), sizes[0] if sizes else 0, sizes[-1] if sizes else 0, len(mtaps), nbuf, REP))


if __name__ == "__main__":
    main()
