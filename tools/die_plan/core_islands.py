#!/usr/bin/env python3
"""MASTER-PLAN in-core island siting, SRAM-aware (METHODOLOGY 12.2a1 / 12.8b, COORD 10-26 QC-SU-LAT-R5 ruling).

The plan sites the k in-core tree islands of a hard core (pushdown driver cells at fixed coordinates) so that
  * every island is LEGAL: its 8.64 um square (4.32 lattice) clears every macro by the halo;
  * every island is within max_entry_um MAZE distance (legal Manhattan path around the macros) of the centre
    clock entry -- R5 btab island Q1 was 199.8 um maze from the entry (SRAM column in the way);
  * the sinks split into k EQUAL-load groups (balanced power diagram on maze distance), each island at the legal
    lattice site minimising its group's p95 maze reach, so the shared H-tree planner (core_infra_htree.py)
    can give every level one wire length / repeater count.
Plan-only geometry (placed sink + macro dump of the core, `geo` format of the QC-SU-LAT kits: CORE / PIN ck /
SINK x y cell inst pin / MACRO name master x0 y0 x1 y1 CK x y); no timing input, no measurement.
"""
import collections
import json
import sys
from pathlib import Path

import numpy as np

LAT = 4.32
ISL_HALF = 4.32


def snap(v):
    return round(round(v / LAT) * LAT, 3)


def read_geo(path):
    core, entry, sinks, macros = None, None, [], []
    for line in open(path):
        f = line.split()
        if not f:
            continue
        if f[0] == "CORE":
            core = tuple(map(float, f[1:5]))
        elif f[0] == "PIN" and f[1] == "ck":
            entry = (float(f[2]), float(f[3]))
        elif f[0] == "SINK":
            sinks.append((float(f[1]), float(f[2])))
        elif f[0] == "MACRO":
            rect = tuple(map(float, f[3:7]))
            ck = (float(f[8]), float(f[9])) if len(f) > 9 and f[7] == "CK" else None
            macros.append(dict(name=f[1], rect_um=list(rect), ck_um=list(ck) if ck else None))
    if core is None or entry is None:
        raise ValueError(f"{path}: geo needs CORE and PIN ck")
    for m in macros:
        if m["ck_um"]:
            sinks.append(tuple(m["ck_um"]))
    return dict(core_um=list(core), entry_um=list(entry), sinks=sinks, macros=macros)


class Grid:
    def __init__(self, core, macros, g=1.08, halo=2.2):
        self.x0, self.y0, self.g = core[0], core[1], g
        self.nx = int((core[2] - core[0]) / g) + 1
        self.ny = int((core[3] - core[1]) / g) + 1
        xs = self.x0 + np.arange(self.nx) * g
        ys = self.y0 + np.arange(self.ny) * g
        X, Y = np.meshgrid(xs, ys, indexing="ij")
        self.blk = np.zeros((self.nx, self.ny), bool)
        for m in macros:
            r = m["rect_um"]
            self.blk |= (X > r[0] - halo) & (X < r[2] + halo) & (Y > r[1] - halo) & (Y < r[3] + halo)
        self.macros, self.halo, self._d = macros, halo, {}

    def cell(self, p):
        i = min(self.nx - 1, max(0, round((p[0] - self.x0) / self.g)))
        j = min(self.ny - 1, max(0, round((p[1] - self.y0) / self.g)))
        if not self.blk[i, j]:
            return (i, j)
        free = np.argwhere(~self.blk)
        k = np.argmin(np.abs(free[:, 0] - i) + np.abs(free[:, 1] - j))
        return tuple(free[k])

    def dist(self, p):
        """maze (4-neighbour, legal cells only) distance field in um from point p; inf where unreachable."""
        c = self.cell(p)
        if c in self._d:
            return self._d[c]
        D = np.full((self.nx, self.ny), np.inf)
        D[c] = 0
        q = collections.deque([c])
        blk, nx, ny = self.blk, self.nx, self.ny
        Di = np.full((nx, ny), -1, np.int32)
        Di[c] = 0
        while q:
            a, b = q.popleft()
            d = Di[a, b] + 1
            for na, nb in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                if 0 <= na < nx and 0 <= nb < ny and Di[na, nb] < 0 and not blk[na, nb]:
                    Di[na, nb] = d
                    q.append((na, nb))
        D = np.where(Di >= 0, Di * self.g, np.inf)
        self._d[c] = D
        return D

    def island_legal(self, c, core):
        r = (c[0] - ISL_HALF, c[1] - ISL_HALF, c[0] + ISL_HALF, c[1] + ISL_HALF)
        if r[0] < core[0] or r[1] < core[1] or r[2] > core[2] or r[3] > core[3]:
            return False
        return not any(r[0] < m["rect_um"][2] + self.halo and r[2] > m["rect_um"][0] - self.halo and
                       r[1] < m["rect_um"][3] + self.halo and r[3] > m["rect_um"][1] - self.halo
                       for m in self.macros)


def balanced(cost, iters=400):
    """equal-count assignment of n points to k centres minimising cost (n x k) -- power diagram + exact fix-up."""
    n, k = cost.shape
    tgt = [n // k + (1 if i < n % k else 0) for i in range(k)]
    w = np.zeros(k)
    a = np.argmin(cost, 1)
    for it in range(iters):
        a = np.argmin(cost + w, 1)
        cnt = np.bincount(a, minlength=k)
        if all(cnt[c] == tgt[c] for c in range(k)):
            break
        w += 0.5 * (cnt - np.array(tgt)) / max(1, n / k) * 20 / (1 + it / 50)
    cnt = np.bincount(a, minlength=k)
    while any(cnt[c] > tgt[c] for c in range(k)):
        best = None
        for c in range(k):
            if cnt[c] <= tgt[c]:
                continue
            idx = np.where(a == c)[0]
            for d in range(k):
                if cnt[d] < tgt[d]:
                    delta = cost[idx, d] - cost[idx, c]
                    j = int(np.argmin(delta))
                    if best is None or delta[j] < best[0]:
                        best = (delta[j], idx[j], d)
        _, i, d = best
        cnt[a[i]] -= 1
        cnt[d] += 1
        a[i] = d
    return a


def site(geo, k=4, max_entry_um=110.0, pct=95, rounds=6, sample=1500, seed=1, sep_um=17.28):
    core, entry = geo["core_um"], tuple(geo["entry_um"])
    G = Grid(core, geo["macros"])
    De = G.dist(entry)
    pts = np.array(geo["sinks"])
    rng = np.random.default_rng(seed)
    if len(pts) > sample:
        pts = pts[rng.choice(len(pts), sample, replace=False)]
    sc = np.array([G.cell(p) for p in pts])
    # candidate island centres: 4.32 lattice, legal square, maze distance from entry <= max_entry_um
    cand = []
    for x in np.arange(snap(core[0] + ISL_HALF), core[2] - ISL_HALF + 1e-6, LAT):
        for y in np.arange(snap(core[1] + ISL_HALF), core[3] - ISL_HALF + 1e-6, LAT):
            c = (round(float(x), 3), round(float(y), 3))
            if G.island_legal(c, core) and De[G.cell(c)] <= max_entry_um:
                cand.append(c)
    if len(cand) < k:
        raise ValueError(f"only {len(cand)} legal island sites within {max_entry_um} um maze of the entry")
    cand_a = np.array(cand)
    # seeds: k-way median split of the sinks (W/E then N/S for k=4), nearest feasible candidates
    order = np.argsort(pts[:, 0])
    halves = [order[: len(order) // 2], order[len(order) // 2:]]
    seeds = []
    for h in halves:
        o = h[np.argsort(pts[h, 1])]
        for part in np.array_split(o, k // 2):
            m = np.median(pts[part], 0)
            ok = [i for i in np.argsort(np.abs(cand_a - m).sum(1))
                  if all(abs(cand_a[i][0] - q[0]) + abs(cand_a[i][1] - q[1]) >= sep_um for q in seeds)]
            seeds.append(tuple(map(float, cand_a[ok[0]])))
    cur = seeds
    for _ in range(rounds):
        cost = np.stack([G.dist(c)[sc[:, 0], sc[:, 1]] for c in cur], 1)
        a = balanced(cost)
        new = []
        for c in range(k):
            g = sc[a == c]
            m = np.median(pts[a == c], 0)
            others = new + cur[c + 1:]
            ok = [i for i in np.argsort(np.abs(cand_a - m).sum(1))
                  if all(abs(cand_a[i][0] - q[0]) + abs(cand_a[i][1] - q[1]) >= sep_um for q in others)][:40]
            best = None
            for s in [tuple(map(float, cand_a[i])) for i in ok]:
                v = De[G.cell(s)] + np.percentile(G.dist(s)[g[:, 0], g[:, 1]], pct)
                if best is None or v < best[0]:
                    best = (v, s)
            new.append(best[1])
        if not new or new == cur:
            break
        cur = new
    cost = np.stack([G.dist(c)[sc[:, 0], sc[:, 1]] for c in cur], 1)
    a = balanced(cost)
    isl = []
    for c in range(k):
        d = cost[a == c, c]
        x, y = cur[c]
        isl.append(dict(centre_um=[x, y], rect_um=[round(x - ISL_HALF, 3), round(y - ISL_HALF, 3),
                                                     round(x + ISL_HALF, 3), round(y + ISL_HALF, 3)],
                        entry_maze_um=round(float(De[G.cell((x, y))]), 2), load_frac=round(float((a == c).mean()), 4),
                        reach_um=dict(mean=round(float(d.mean()), 1), p95=round(float(np.percentile(d, 95)), 1),
                                      max=round(float(d.max()), 1))))
    em = [q["entry_maze_um"] for q in isl]
    return dict(method="core_islands.site (SRAM-aware maze, equal-load, entry <= max_entry_um)",
                k=k, max_entry_um=max_entry_um, entry_um=list(entry), sinks=len(geo["sinks"]),
                sampled=int(len(pts)), islands=isl,
                entry_maze_um=dict(min=min(em), max=max(em)),
                leaf_reach_um=max(q["reach_um"]["p95"] for q in isl),
                # equal-structure tree (every level padded to its longest edge): root->sink wire >= this
                equal_path_um=round(max(em) + max(q["reach_um"]["max"] for q in isl), 1),
                floor_entry_to_sink_maze_um=round(float(max(De[G.cell(p)] for p in geo["sinks"])), 1),
                verdict="PASS" if max(em) <= max_entry_um + 1e-6 else "FAIL")


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("geo", nargs="+", help="MODULE=geo_file")
    p.add_argument("--k", type=int, default=4)
    p.add_argument("--max-entry-um", type=float, default=110.0)
    p.add_argument("--out", required=True, help="output JSON {module: site result}")
    a = p.parse_args(argv)
    res = {}
    for spec in a.geo:
        mod, f = spec.split("=", 1)
        res[mod] = site(read_geo(f), a.k, a.max_entry_um)
        r = res[mod]
        print(mod, r["verdict"], "entry_maze", r["entry_maze_um"], "p95 reach", r["leaf_reach_um"],
              "equal_path", r["equal_path_um"], "floor", r["floor_entry_to_sink_maze_um"],
              [q["centre_um"] for q in r["islands"]])
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    return 0 if all(r["verdict"] == "PASS" for r in res.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
