#!/usr/bin/env python3
"""S81-DIEPLACE (10-19): physically legal, degree-capped regional reset tree (opt-in, OT_RESET_LEGAL=<obstacles.json>).

The default dv_bind.reset_tree picks reset station POINTS that avoid block outlines only; dv_rvcase then spirals each
17.28-um dsfd_rly_1 body out of lanes / relays / landings, up to 1200 um away (first physical case failed at
st_rs_39_18_2; the old netlist on legal bodies had 1003/5183 reset edges > 405 um).  This module instead:

  * reads the ACTUAL obstacle rectangles dv_rvcase reserves before it places reset bodies (blocks, relay station
    bodies, CLOSED landing LEF footprints at their placed points, realized lane bands) -- `dv_rvcase --dump-obstacles`;
  * enumerates mutually non-overlapping R0 reset-body slots (lower-left on the 0.048-um signal-track origin lattice,
    0.5-um clearance, the placer's die-edge keepout) on a 200-um sampling grid plus every obstacle edge;
  * builds the tree by BFS with at most CHILD_CAP children per station (2 logical loads each: .i + .rs) and at most
    SINK_CAP production sink loads per station, using EXACT R0 pin-to-pin Manhattan reach: parent .o -> child .i AND
    child .rs <= 405 um; parent .o -> sink pin <= 405 um;
  * delivers every reset release edge the landing calendar needs (hop-0 gate enable at the source pin, landing rs at the
    PLACED landing body) from a station of exactly that release depth within reach, or from a shallower station through
    a chain of calendar stations on legal slots, each hop within reach.  No edge is relaxed; impossible -> ValueError.

dv_rvcase places every body exactly at its slot (no spiral) and re-checks every reset connection on the placed bodies.
This is a GEOMETRY + NETLIST input for GEN, not a routed/timed result (native regional clock / RC / PG still owed).
"""
import collections
import json
import math

REACH = 405.0
GRID_L = 200.0
GRID_O = 0.048                    # signal-track origin lattice (reset_space_1019 lattice probe, R0)
GAP = 0.5
EDGE = 1.2                        # dv_rvcase.Placer die-edge keepout
CHILD_CAP = 8
SINK_CAP = 16
PER_CELL = 10                     # slots per 200-um sampling cell (calendar chains need free legal bodies near sinks)
SPACING = 40.0
# dsfd_rly_1_WN R0 pin centres (LEF: i W-face mid, rs S-face, o N-face)
PIN_O = (9.084, 17.28)
PIN_I = (0.0, 8.7)
PIN_RS = (8.124, 0.0)


class Occ:
    B = 200.0

    def __init__(self, W, H):
        self.W, self.H = W, H
        self.buck = collections.defaultdict(list)

    def add(self, r):
        for i in range(int(r[0] // self.B), int(r[2] // self.B) + 1):
            for j in range(int(r[1] // self.B), int(r[3] // self.B) + 1):
                self.buck[(i, j)].append(r)

    def hits(self, r, gap=GAP):
        x0, y0, x1, y1 = r
        if x0 < EDGE or y0 < EDGE or x1 > self.W - EDGE or y1 > self.H - EDGE:
            return True
        for i in range(int((x0 - gap) // self.B), int((x1 + gap) // self.B) + 1):
            for j in range(int((y0 - gap) // self.B), int((y1 + gap) // self.B) + 1):
                for a in self.buck.get((i, j), ()):
                    if a[0] < x1 + gap and x0 < a[2] + gap and a[1] < y1 + gap and y0 < a[3] + gap:
                        return True
        return False

    def edges_near(self, x0, y0, x1, y1):
        seen = set()
        for i in range(int(x0 // self.B), int(x1 // self.B) + 1):
            for j in range(int(y0 // self.B), int(y1 // self.B) + 1):
                for a in self.buck.get((i, j), ()):
                    if a not in seen:
                        seen.add(a)
                        yield a


def snap(v, up):
    k = v / GRID_O
    return round((math.ceil(k - 1e-9) if up else math.floor(k + 1e-9)) * GRID_O, 3)


def pin(ll, off):
    return (ll[0] + off[0], ll[1] + off[1])


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def hop_um(pll, cll):
    """parent .o -> child .i and child .rs (both loads of the parent's net)"""
    o = pin(pll, PIN_O)
    return max(man(o, pin(cll, PIN_I)), man(o, pin(cll, PIN_RS)))


def sink_um(pll, xy):
    return man(pin(pll, PIN_O), xy)


def slots(W, H, rects, size):
    """mutually non-overlapping legal R0 lower-left slots; deterministic"""
    rw, rh = size
    occ = Occ(W, H)
    for r in rects:
        occ.add(tuple(r))
    taken = Occ(W, H)
    out = []
    nx, ny = int(math.ceil(W / GRID_L)), int(math.ceil(H / GRID_L))
    for i in range(nx):
        for j in range(ny):
            x0, y0 = i * GRID_L, j * GRID_L
            xs = {x0 + f * GRID_L - rw / 2 for f in (0.1, 0.3, 0.5, 0.7, 0.9)}
            ys = {y0 + f * GRID_L - rh / 2 for f in (0.1, 0.3, 0.5, 0.7, 0.9)}
            for a in occ.edges_near(x0, y0, x0 + GRID_L, y0 + GRID_L):
                for v in (a[0] - rw - GAP - 0.05, a[2] + GAP + 0.05):
                    if x0 <= v < x0 + GRID_L:
                        xs.add(v)
                for v in (a[1] - rh - GAP - 0.05, a[3] + GAP + 0.05):
                    if y0 <= v < y0 + GRID_L:
                        ys.add(v)
            cx, cy = x0 + GRID_L / 2, y0 + GRID_L / 2
            got = []
            for x, y in sorted(((snap(x, x > cx), snap(y, y > cy)) for x in xs for y in ys),
                               key=lambda p: (abs(p[0] + rw / 2 - cx) + abs(p[1] + rh / 2 - cy), p)):
                r = (x, y, x + rw, y + rh)
                if occ.hits(r) or taken.hits(r, gap=GAP):
                    continue
                if all(abs(x - u) + abs(y - w) >= SPACING for u, w in got):
                    got.append((x, y))
                    taken.add(r)
                    if len(got) == PER_CELL:
                        break
            out += got
    return out


class LegalTree:
    def __init__(self, W, H, obst):
        self.W, self.H = W, H
        self.size = tuple(obst.get('reset_size', (17.28, 17.28)))
        self.S = slots(W, H, obst['rects'], self.size)
        self.B = REACH
        self.buck = collections.defaultdict(list)
        for k, (x, y) in enumerate(self.S):
            self.buck[(int(x // self.B), int(y // self.B))].append(k)
        self.par, self.dep, self.kids, self.loads = {}, {}, collections.Counter(), collections.Counter()
        self.used = set()            # slots that become cells: ancestors of every served / delivered node
        self.moved = set()           # unused BFS slots re-parented as calendar-chain stations
        self.chain_cache = {}
        self.chains = 0

    def near_slots(self, xy, r):
        n = int(math.ceil((r + 40.0) / self.B))
        bx, by = int(xy[0] // self.B), int(xy[1] // self.B)
        for dx in range(-n, n + 1):
            for dy in range(-n, n + 1):
                for k in self.buck.get((bx + dx, by + dy), ()):
                    if man(self.S[k], xy) <= r + 40.0:
                        yield k

    def build(self, root_xy):
        root = min(range(len(self.S)), key=lambda k: (man(self.S[k], root_xy), k))
        self.root = root
        self.par[root] = None; self.dep[root] = 0
        q = collections.deque([root])
        while q:
            c = q.popleft()
            for m in sorted(self.near_slots(self.S[c], REACH), key=lambda m: (man(self.S[c], self.S[m]), m)):
                if self.kids[c] >= CHILD_CAP:
                    break
                if m not in self.par and hop_um(self.S[c], self.S[m]) <= REACH:
                    self.par[m] = c; self.dep[m] = self.dep[c] + 1; self.kids[c] += 1
                    q.append(m)
        self.mark(root)
        return root

    def mark(self, k):
        while k is not None and k not in self.used:
            self.used.add(k); k = self.par[k]

    def clean(self, k):
        """k's BFS ancestor path holds no re-parented slot (its depth is still valid)"""
        while k is not None:
            if k in self.moved:
                return False
            k = self.par[k]
        return True

    def serve(self, xy):
        """min-depth tree slot within sink reach of xy with sink capacity (None if none)"""
        best = None
        for k in self.near_slots(xy, REACH):
            if k in self.par and self.loads[k] < SINK_CAP and sink_um(self.S[k], xy) <= REACH and self.clean(k):
                key = (self.dep[k], sink_um(self.S[k], xy), k)
                if best is None or key < best:
                    best = key
        if best is None:
            return None
        self.loads[best[2]] += 1; self.mark(best[2])
        return best[2]

    def min_dep(self, xy, slack=0.0):
        """smallest clean tree depth whose station output reaches xy (None: unreachable)"""
        ds = [self.dep[k] for k in self.near_slots(xy, REACH)
              if k in self.par and sink_um(self.S[k], xy) + slack <= REACH and self.clean(k)]
        return min(ds) if ds else None

    def deliver_slack(self, depth, xy, slack, tag):
        R = REACH - slack
        return self.deliver(depth, xy, tag, R)

    def deliver(self, depth, xy, tag, R=REACH):
        """a node whose output releases at tree depth `depth` and drives a sink at xy within reach.
        Direct when a clean tree node of that depth is in reach; else a calendar chain of n >= 1 stations on slots no
        cell uses, from a node of depth - n (deepest feasible first), every hop <= REACH."""
        key = (depth, round(xy[0] / 25), round(xy[1] / 25), round(R))
        c = self.chain_cache.get(key)
        if c is not None and self.loads[c] < SINK_CAP and sink_um(self.S[c], xy) <= R:
            self.loads[c] += 1
            return c
        for k in sorted(self.near_slots(xy, REACH), key=lambda k: (sink_um(self.S[k], xy), k)):
            if (k in self.par and self.dep[k] == depth and self.loads[k] < SINK_CAP and sink_um(self.S[k], xy) <= R
                    and self.clean(k)):
                self.loads[k] += 1; self.mark(k); self.chain_cache[key] = k
                return k
        for n in range(1, depth + 1):
            r = n * REACH + REACH
            for a in sorted((k for k in self.near_slots(xy, r) if k in self.par and self.dep[k] == depth - n
                             and self.kids[k] < CHILD_CAP and k not in self.moved),
                            key=lambda k: (man(self.S[k], xy), k)):
                if man(pin(self.S[a], PIN_O), xy) > n * REACH + R or not self.clean(a):
                    continue
                path = self._chain(a, n, xy, R)
                if path:
                    self.mark(a)
                    prev = a
                    for s in path:
                        old = self.par.get(s)
                        if old is not None:
                            self.kids[old] -= 1
                        self.moved.add(s)
                        self.par[s] = prev; self.dep[s] = self.dep[prev] + 1; self.kids[prev] += 1
                        self.used.add(s); prev = s
                    self.loads[prev] += 1; self.chain_cache[key] = prev; self.chains += 1
                    return prev
        raise ValueError(f'reset_legal: no legal release of depth {depth} at {xy} ({tag})')

    def _chain(self, a, n, xy, R=REACH):
        prev, path, fset = a, [], set()
        for k in range(1, n + 1):
            t = (self.S[a][0] + (xy[0] - self.S[a][0]) * k / n, self.S[a][1] + (xy[1] - self.S[a][1]) * k / n)
            best = None
            for s in self.near_slots(t, REACH):
                if s in self.used or s in fset or s in self.moved:
                    continue
                if hop_um(self.S[prev], self.S[s]) > REACH:
                    continue
                d_end = sink_um(self.S[s], xy)
                if (k == n and d_end > R) or d_end > (n - k) * (REACH - 40.0) + R:
                    continue
                kk = (self.kids[s] > 0, man(self.S[s], t), s)
                if best is None or kk < best:
                    best = kk
            if best is None:
                return None
            path.append(best[-1]); fset.add(best[-1]); prev = best[-1]
        return path

    def check(self):
        """every used edge and the caps, re-measured"""
        bad = [(k, self.par[k], round(hop_um(self.S[self.par[k]], self.S[k]), 3)) for k in self.used
               if self.par[k] is not None and hop_um(self.S[self.par[k]], self.S[k]) > REACH]
        kids = collections.Counter(self.par[k] for k in self.used if self.par[k] is not None)
        return dict(nodes=len(self.used), chain_stations=len(self.moved), chains=self.chains, over_reach=bad[:20],
                    n_over_reach=len(bad), max_children=max(kids.values()) if kids else 0,
                    max_sink_loads=max(self.loads.values()) if self.loads else 0,
                    max_depth=max(self.dep[k] for k in self.used),
                    max_hop_um=round(max((hop_um(self.S[self.par[k]], self.S[k]) for k in self.used if self.par[k] is not None), default=0), 3),
                    slots=len(self.S), bfs_reached=len(self.par))


def load_obstacles(path):
    o = json.load(open(path))
    assert o.get('schema') == 'opentallas.s81_dv.reset_obstacles.v1', path
    return o
