"""QC-A0 10-24 (GEOM-REVIEW batch 1, 08:55): ft slots of partitions with hard cores declared no station sites, so G0 /
face_flops.tcl interpolate station j at L*j/k along the in->out route -- 252 of those points landed INSIDE A0 / SU hard
cores (cbn_q01 96, cbn_q00 48, cbf_q01 46, cbf_*_s2 26, sl*_su_c / su_l1 36), where no std cell can sit, and the
straight in->out routes ran across cores that use the partition's own signal layers (A0 / SU cores route to M7).

ft_regs_off_cores(plan) checks every ft slot of every type with hard cores on a routing grid (GRID um cells; a cell
whose centre lies in a hard core is blocked, all layers <= M7 belong to the core): hop length = the shortest rectilinear
path AROUND the cores (BFS), not the Manhattan distance.  A slot with a station inside a core (+ HALO) or a hop longer
than its limit (min(lane reach, budgets.ft_station_max_um) - GRID snap margin) gets declared regs_um (type frame,
station 0 = the in pin): stations 1..k-1 move by coordinate descent to channel sites (>= HALO from every core, HALO_MIN
as the last resort) that minimise the longest of their two hops, ties -> not crowded (>= SEP um from other slots'
sites) -> nearest to the current point.  Slots that still miss the limit are returned in `unfixed`.

    python3 ft_regs.py die_plan.json [--inplace]        (report / fix a plan file)"""
import collections
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools" / "die_plan"))
import check  # noqa: E402
import schema  # noqa: E402

HALO = 8.64
HALO_MIN = 2.16
GRID = 8.64
SEP = 12.0
ADD_STATIONS = True       # OWNER 10-24 18:4x: more stations allowed (same rebind)


class Grid:
    def __init__(self, W, H, cores, g=GRID):
        self.g, self.W, self.H = g, W, H
        self.nx, self.ny = int(np.ceil(W / g)), int(np.ceil(H / g))
        cx = (np.arange(self.nx) + 0.5) * g
        cy = (np.arange(self.ny) + 0.5) * g
        self.X, self.Y = np.meshgrid(cx, cy, indexing="ij")
        self.cores = cores
        self.blocked = self._in(cores, 0.0)
        self._cache = {}

    def _in(self, cores, halo):
        m = np.zeros((self.nx, self.ny), bool)
        for x0, y0, x1, y1 in cores:
            m |= (self.X >= x0 - halo) & (self.X <= x1 + halo) & (self.Y >= y0 - halo) & (self.Y <= y1 + halo)
        return m

    def sites(self, halo):
        ok = ~self._in(self.cores, halo)
        ok[0, :] = ok[-1, :] = ok[:, 0] = ok[:, -1] = False
        return ok

    def cell(self, p):
        return (min(self.nx - 1, max(0, int(p[0] / self.g))), min(self.ny - 1, max(0, int(p[1] / self.g))))

    def dist(self, p):
        """rectilinear shortest path length (um) from p to every cell centre, around the cores."""
        c = self.cell(p)
        if c in self._cache:
            return self._cache[c]
        d = np.full((self.nx, self.ny), np.inf)
        bl, g, nx, ny = self.blocked, self.g, self.nx, self.ny
        if not bl[c]:
            d[c] = 0.0
            seeds = [c]
        else:   # p inside a core (a station to be moved): leave the core by the shortest way, then route around
            comp, st, edge = {c}, [c], set()
            while st:
                i, j = st.pop()
                for a, b in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                    if 0 <= a < nx and 0 <= b < ny:
                        if bl[a, b] and (a, b) not in comp:
                            comp.add((a, b))
                            st.append((a, b))
                        elif not bl[a, b]:
                            edge.add((a, b))
            for e in edge:
                d[e] = abs(e[0] - c[0]) * g + abs(e[1] - c[1]) * g
            seeds = sorted(edge, key=lambda e: d[e])
        # Dijkstra-light: seeds carry different start costs -> a heap
        import heapq
        q = [(d[e], e) for e in seeds]
        heapq.heapify(q)
        while q:
            dd, (i, j) = heapq.heappop(q)
            if dd > d[i, j]:
                continue
            dv = dd + g
            for a, b in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                if 0 <= a < nx and 0 <= b < ny and not bl[a, b] and dv < d[a, b]:
                    d[a, b] = dv
                    heapq.heappush(q, (dv, (a, b)))
        # snap: the exact offset of p inside its cell is within g/2 per axis
        self._cache[c] = d
        return d

    def hop(self, p, q):
        if not self.blocked[self.cell(q)]:
            return float(self.dist(p)[self.cell(q)])
        if not self.blocked[self.cell(p)]:
            return float(self.dist(q)[self.cell(p)])
        return 3.0 * (abs(p[0] - q[0]) + abs(p[1] - q[1]))       # both inside cores: only ever a 'bad' start state


def _inside(p, boxes, halo):
    return any(x0 - halo <= p[0] <= x1 + halo and y0 - halo <= p[1] <= y1 + halo for x0, y0, x1, y1 in boxes)


def _descend(G, regs, out_pt, site_ok, taken, lim, passes=60):
    k = len(regs)
    crowd = np.zeros(site_ok.shape, bool)
    for r in taken:
        crowd |= (np.abs(G.X - r[0]) + np.abs(G.Y - r[1])) < SEP
    for _ in range(passes):
        moved = False
        for j in range(1, k):
            nxt = regs[j + 1] if j + 1 < k else out_pt
            h = np.maximum(G.dist(regs[j - 1]), G.dist(nxt))
            disp = np.abs(G.X - regs[j][0]) + np.abs(G.Y - regs[j][1])
            score = np.where(site_ok, np.where(h > lim, 1e9 + h, crowd * 1e6 + h * 1e-3 + disp * 1e-6), np.inf)
            i = np.unravel_index(int(np.argmin(score)), score.shape)
            if not np.isfinite(score[i]):
                break
            new = (round(float(G.X[i]), 3), round(float(G.Y[i]), 3))
            if new != tuple(regs[j]):
                cur = G.cell(regs[j])
                if score[i] < score[cur] - 1e-9 or not site_ok[cur]:
                    regs[j] = new
                    moved = True
        if not moved:
            break
    hops = [G.hop(p, q) for p, q in zip(regs, regs[1:] + [out_pt])]
    return regs, hops


def ft_regs_off_cores(raw, log=print):
    P = schema.Plan(raw)
    smax = float(raw.get("budgets", {}).get("ft_station_max_um", 750.0))
    first, lim = {}, {}
    for lid, ln in P.lanes.items():
        reach = float(ln.get("reach_um", P.reach))
        for part, slot, a, b in P.lane_crossings(lid):
            if slot is None:
                continue
            key = (P.parts[part]["type"], slot)
            first.setdefault(key, (part, a, b))
            lim[key] = min(lim.get(key, smax), reach, smax)
    stats = dict(checked=0, slots=0, stations_in_cores=0, long_hops=0, unfixed=[])
    grids = {}
    for (tn, sn), (part, a, b) in sorted(first.items()):
        t = P.types[tn]
        hcs = t.get("hard_cores") or []
        if not hcs:
            continue
        s = P.slot(part, sn)
        k = int(s.get("stations", 1))
        W, H = t["outline_um"]
        boxes = [(c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0],
                  c["origin_um"][1] + c["outline_um"][1]) for c in hcs]
        if tn not in grids:
            grids[tn] = Grid(W, H, boxes)
        G = grids[tn]
        stats["checked"] += 1
        pa, pb = P.port_point(a), P.port_point(b)
        if s.get("regs_um"):
            regs = [tuple(r) for r in s["regs_um"]]
        else:
            seg = check.zroute(pa, pb, P.die_face(part, s["in_face"]), P.die_face(part, s["out_face"]))
            L = check.plen(seg)
            regs = [P.to_type(part, check.point_at(seg, L * j / k)) for j in range(k)]
        W1 = lambda p: (round(min(max(p[0], 1.0), W - 1.0), 3), round(min(max(p[1], 1.0), H - 1.0), 3))  # noqa: E731
        regs[0] = W1(regs[0])
        out_pt = W1(P.to_type(part, pb))
        hl = lim[(tn, sn)] - G.g                      # grid snap margin: G0 measures the exact (Manhattan) hop
        bad = [j for j in range(1, k) if _inside(regs[j], boxes, HALO)]
        hops0 = [G.hop(p, q) for p, q in zip(regs, regs[1:] + [out_pt])]
        if not bad and max(hops0) <= hl:
            continue
        stats["slots"] += 1
        stats["stations_in_cores"] += len(bad)
        stats["long_hops"] += sum(1 for h in hops0 if h > hl)
        taken = [tuple(r) for s2 in t["ft_slots"] if s2 is not s for r in s2.get("regs_um", [])[1:]]
        why = f"stations {bad} in cores" if bad else ""
        if max(hops0) > hl:
            why += (", " if why else "") + f"routed hops {[round(h) for h in hops0]}"
        best = None
        for halo in (HALO, HALO_MIN):
            r2, hops = _descend(G, list(regs), out_pt, G.sites(halo), taken, hl)
            if best is None or max(hops) < max(best[1]):
                best = (r2, hops, halo)
            if max(hops) <= hl:
                break
        regs, hops, halo = best
        ok = max(hops) <= hl
        k0 = k
        while not ok and ADD_STATIONS and k < k0 + 3:
            # OWNER 10-24 18:4x: a slot whose routed hops cannot meet the limit gets one more station (bound RTL + R8 +
            # latency follow in the same rebind): insert it in the longest hop, then descend again
            i = int(np.argmax(hops))
            a_, b_ = regs[i], (regs[i + 1] if i + 1 < k else out_pt)
            regs = regs[:i + 1] + [((a_[0] + b_[0]) / 2, (a_[1] + b_[1]) / 2)] + regs[i + 1:]
            k += 1
            best = None
            for halo in (HALO, HALO_MIN):
                r2, h2 = _descend(G, list(regs), out_pt, G.sites(halo), taken, hl)
                if best is None or max(h2) < max(best[1]):
                    best = (r2, h2, halo)
                if max(h2) <= hl:
                    break
            regs, hops, halo = best
            ok = max(hops) <= hl
        if k != k0:
            s["stations"] = k
            stats.setdefault("added_stations", []).append(dict(slot=f"{tn}.{sn}", stations_from=k0, stations_to=k,
                                                               routed_hops=[round(h) for h in hops]))
            why += f"; stations {k0} -> {k}"
        if k > 1 or bad:
            s["regs_um"] = [[round(x, 3), round(y, 3)] for x, y in regs]
        if not ok:
            stats["unfixed"].append(dict(slot=f"{tn}.{sn}", stations=k, routed_hops=[round(h) for h in hops],
                                         limit=round(hl + G.g), stations_needed=k + int(np.ceil(
                                             (sum(hops) - hl * (k + 1)) / hl)) if sum(hops) > hl * (k + 1) else k + 1))
        log(f"ft_regs: {tn}.{sn} k={k}: {why} -> routed hops {[round(h) for h in hops]} (limit {hl:.0f}, core clearance "
            f"{halo}){'' if ok else ' -- LIMIT NOT MET'}")
    return stats


if __name__ == "__main__":
    path = Path(sys.argv[1])
    raw = json.loads(path.read_text())
    st = ft_regs_off_cores(raw)
    print("ft_regs:", json.dumps(st))
    if "--inplace" in sys.argv:
        path.write_text(json.dumps(raw, indent=1) + "\n")
