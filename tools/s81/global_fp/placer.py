#!/usr/bin/env python3
"""GLOBAL-FP-S slot-stack annealer for the S81 hub region (screen only).

Legal-by-construction representation: the hub region between the two field halves is split by ONE full-width
horizontal crossing corridor (field trees and link bundles cross the spine there, replaces vch/hc_corridor); each
tier (below / above the corridor) is a left-to-right sequence of columns; each column is a bottom-to-top (or
top-to-bottom) stack of blocks, packed against the corridor.  State = (corridor y, block -> tier/column/order,
column order, MIX4 shape).  Infeasibility (column widths > region width, stack height > tier height) is a penalty,
so a zero-penalty result is overlap-free.  Objective (same terms as score.py, fast form):
  sum traffic x length (p2p facing-face + VM internal span; trees = leaf MST + trunk to the root with corridor detour)
  + LAT_W x worst field round trip (um).
"""
import math, random

LAT_W = 566.0 * 0.504757    # worst-field-path weight = one x-broadcast trunk at field duty
HALO = 21.6


def man(p, q):
    return abs(p[0] - q[0]) + abs(p[1] - q[1])


class FastTrees:
    """per tree: fixed leaf wire (MST over leaves, oriented from each candidate attach leaf for collect trees)."""

    def __init__(self, graph, ports, mst_fn):
        self.trees = []
        for e in graph['edges']:
            if e['kind'] != 'tree':
                continue
            leaves = [f for f in e['ends'] if f.startswith('F')]
            pts = [ports[f] for f in leaves]
            W = e['width']
            opts = []
            if e.get('tree_mode') == 'broadcast':
                par = mst_fn(pts, 0)
                wire = sum(man(pts[i], pts[par[i]]) for i in range(1, len(pts))) * W
                opts = [(i, wire) for i in range(len(pts))]           # attach anywhere: same leaf MST
            else:
                bits = [e['leaf_bits'][f] for f in leaves]
                for a in range(len(pts)):
                    par = mst_fn(pts, a)
                    sub = bits[:]
                    order = sorted(range(len(pts)), key=lambda i: -self._depth(par, i))
                    for i in order:
                        if par[i] >= 0:
                            sub[par[i]] += sub[i]
                    wire = sum(man(pts[i], pts[par[i]]) * min(W, sub[i]) for i in range(len(pts)) if par[i] >= 0)
                    opts.append((a, wire))
            half = {f: graph['nodes'][f]['half'] for f in leaves}
            self.trees.append(dict(id=e['id'], root=e['ends'][0], pts=pts, opts=opts, W=W, duty=e['duty'],
                                   mode=e.get('tree_mode'), leaves=leaves, half=[half[f] for f in leaves]))

    @staticmethod
    def _depth(par, i):
        d = 0
        while par[i] != -1:
            i = par[i]; d += 1
        return d


def via_len(rp, lp, corr, direct):
    """root point -> leaf point length; when not direct, the path must cross the spine inside the corridor band"""
    dx = abs(rp[0] - lp[0])
    if direct or corr is None:
        return dx + abs(rp[1] - lp[1])
    lo, hi = sorted((rp[1], lp[1]))
    c0, c1 = corr[1], corr[1] + corr[3]
    if hi < c0:
        return dx + (hi - lo) + 2 * (c0 - hi)
    if lo > c1:
        return dx + (hi - lo) + 2 * (lo - c1)
    return dx + (hi - lo)


def nearest_on_rect(r, p):
    x, y, w, h = r
    return [min(max(p[0], x), x + w), min(max(p[1], y), y + h)]


def tree_cost(T, rects, corr, region_x):
    """fast: returns (traffic_wire, {leaf: root path})"""
    r = rects[T['root']]
    west_direct = r[0] <= region_x[0] + 60
    east_direct = r[0] + r[2] >= region_x[1] - 60
    cx = sum(p[0] for p in T['pts']) / len(T['pts']); cy = sum(p[1] for p in T['pts']) / len(T['pts'])
    best = None
    for a, wire in T['opts']:
        lp = T['pts'][a]
        rp = nearest_on_rect(r, lp)
        direct = (T['half'][a] == 'W' and west_direct) or (T['half'][a] == 'E' and east_direct)
        c = wire + T['W'] * via_len(rp, lp, corr, direct)
        if best is None or c < best[0]:
            best = (c, a)
        if T['mode'] == 'broadcast':
            break
    # broadcast: attach leaf = leaf nearest the root
    if T['mode'] == 'broadcast':
        rp0 = nearest_on_rect(r, [cx, cy])
        a = min(range(len(T['pts'])), key=lambda i: man(rp0, T['pts'][i]))
        lp = T['pts'][a]; rp = nearest_on_rect(r, lp)
        direct = (T['half'][a] == 'W' and west_direct) or (T['half'][a] == 'E' and east_direct)
        best = (T['opts'][0][1] + T['W'] * via_len(rp, lp, corr, direct), a)
    paths = {}
    for f, lp, h in zip(T['leaves'], T['pts'], T['half']):
        rp = nearest_on_rect(r, lp)
        direct = (h == 'W' and west_direct) or (h == 'E' and east_direct)
        paths[f] = via_len(rp, lp, corr, direct)
    return best[0] * T['duty'], paths


class SlotStack:
    def __init__(self, graph, score_mod, movable, dims, region, vm_shape, fixed_rects, seed=1, mix_shapes=None):
        self.g = graph; self.S = score_mod
        self.mov = list(movable); self.dims = dict(dims)
        self.region = region          # x0, y0, x1, y1
        self.vm_shape = vm_shape
        self.fixed = fixed_rects
        self.rng = random.Random(seed)
        self.mix_shapes = mix_shapes or {}
        ports = {n: v['port'] for n, v in graph['nodes'].items() if 'port' in v}
        self.trees = FastTrees(graph, ports, score_mod.mst).trees
        self.p2p = [e for e in graph['edges'] if e['kind'] == 'p2p']

    # ---------- representation
    def random_state(self, corr_y=None):
        x0, y0, x1, y1 = self.region
        st = dict(corr_y=corr_y if corr_y is not None else (y0 + y1) / 2, tiers={0: [], 1: []},
                  mix=next(iter(self.mix_shapes)) if self.mix_shapes else None)
        blocks = self.mov[:]
        self.rng.shuffle(blocks)
        for b in blocks:
            t = self.rng.randint(0, 1)
            cols = st['tiers'][t]
            if not cols or self.rng.random() < 0.3:
                cols.append([b])
            else:
                self.rng.choice(cols).append(b)
        return st

    def dim(self, st, b):
        if b == 'mix4' and st.get('mix'):
            return self.mix_shapes[st['mix']]
        return self.dims[b]

    def realize(self, st, corr_h=1512.0):
        x0, y0, x1, y1 = self.region
        cy = st['corr_y']
        corr = [x0, cy, x1 - x0, corr_h]
        rects = {}
        pen = 0.0
        for t, cols in st['tiers'].items():
            tier_lo, tier_hi = (y0, cy) if t == 0 else (cy + corr_h, y1)
            widths = [max(self.dim(st, b)[0] for b in c) for c in cols if c]
            cols = [c for c in cols if c]
            total_w = sum(widths) + HALO * max(0, len(widths) - 1)
            pen += max(0.0, total_w - (x1 - x0)) * 1e6
            # spread spare width evenly between columns (channels for stations / bypasses)
            spare = max(0.0, (x1 - x0) - total_w)
            gap = HALO + (spare / (len(widths) - 1) if len(widths) > 1 else 0.0)
            x = x0 if len(widths) > 1 else x0 + spare / 2
            for c, w in zip(cols, widths):
                hsum = sum(self.dim(st, b)[1] for b in c) + HALO * (len(c) - 1)
                pen += max(0.0, hsum - (tier_hi - tier_lo)) * 1e6
                # pack against the corridor
                yy = tier_hi if t == 0 else tier_lo
                for b in (c if t == 1 else c):
                    bw, bh = self.dim(st, b)
                    bx = x + (w - bw) / 2
                    if t == 0:
                        yy -= bh; rects[b] = [bx, yy, bw, bh]; yy -= HALO
                    else:
                        rects[b] = [bx, yy, bw, bh]; yy += bh + HALO
                x += w + gap
        return rects, corr, pen

    # ---------- cost
    def cost(self, st):
        rects, corr, pen = self.realize(st)
        allr = dict(self.fixed); allr.update(rects)
        J = pen
        for e in self.p2p:
            a, b = e['ends']
            if a not in allr or b not in allr:
                continue
            pa, pb = self.S.facing_points(allr[a], allr[b])
            L = man(pa, pb)
            if 'sp_vm' in (a, b):
                L += self.S.vm_internal(allr['sp_vm'], self.vm_shape, pa if a == 'sp_vm' else pb)
            J += e['traffic'] * L
        xp, rp = {}, {}
        for T in self.trees:
            c, paths = tree_cost(T, allr, corr, (self.region[0], self.region[2]))
            J += c
            (xp if T['mode'] == 'broadcast' else rp).update(paths)
        worst = max(xp.get(f, 0) + rp.get(f, 0) for f in set(xp) | set(rp))
        J += LAT_W * worst
        return J, pen, worst

    # ---------- moves
    def neighbour(self, st):
        s = dict(corr_y=st['corr_y'], mix=st.get('mix'), tiers={t: [c[:] for c in cols] for t, cols in st['tiers'].items()})
        r = self.rng.random()
        x0, y0, x1, y1 = self.region
        if r < 0.15:
            s['corr_y'] = min(max(s['corr_y'] + self.rng.gauss(0, 800), y0 + 500), y1 - 2000)
        elif r < 0.2 and self.mix_shapes:
            s['mix'] = self.rng.choice(list(self.mix_shapes))
        elif r < 0.55:
            # move a block to another column (or a new column)
            b = self.rng.choice(self.mov)
            for cols in s['tiers'].values():
                for c in cols:
                    if b in c:
                        c.remove(b)
            t = self.rng.randint(0, 1)
            cols = [c for c in s['tiers'][t] if c]
            s['tiers'][t] = cols
            if not cols or self.rng.random() < 0.15:
                cols.insert(self.rng.randint(0, len(cols)), [b])
            else:
                c = self.rng.choice(cols); c.insert(self.rng.randint(0, len(c)), b)
        elif r < 0.8:
            a, b = self.rng.sample(self.mov, 2)
            for cols in s['tiers'].values():
                for c in cols:
                    for i, v in enumerate(c):
                        if v == a: c[i] = '#'
                        elif v == b: c[i] = a
                    for i, v in enumerate(c):
                        if v == '#': c[i] = b
        else:
            t = self.rng.randint(0, 1)
            cols = s['tiers'][t]
            if len(cols) >= 2:
                i, j = self.rng.sample(range(len(cols)), 2)
                cols[i], cols[j] = cols[j], cols[i]
        for t in s['tiers']:
            s['tiers'][t] = [c for c in s['tiers'][t] if c]
        return s

    def anneal(self, st, iters=60000, T0=None, T1=None):
        J, pen, worst = self.cost(st)
        best = (J, st)
        T0 = T0 or J * 0.05; T1 = T1 or J * 1e-5
        for k in range(iters):
            T = T0 * (T1 / T0) ** (k / iters)
            s2 = self.neighbour(st)
            J2, _, _ = self.cost(s2)
            if J2 < J or self.rng.random() < math.exp(-(J2 - J) / T):
                st, J = s2, J2
                if J < best[0]:
                    best = (J, st)
        return best
