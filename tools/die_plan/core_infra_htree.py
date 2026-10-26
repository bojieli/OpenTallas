#!/usr/bin/env python3
"""Shared core-infra planner: equal-structure in-core clock H-tree (METHODOLOGY 12.8b/c/d1, 12.2a1).

Port of QC-SU-LAT R5 plan_r5.py into tools/die_plan (one generator), with the R6 structure:
  entry -> SPLIT[0] (default 2: W/E) -> SPLIT[1] (2 islands per side) -> SPLIT[2] (B) -> SPLIT[3] (leaf drivers)
* Buffer at EVERY branch point: a node with k children is k co-located branch buffers, each driving ONE
  point-to-point wire to exactly one child.  No net carries two branches, so no Steiner trunk is shared
  between branches (the R5 residual).  The node's input net is a <=2 um local fan (modelled).
* Equal structure: every edge of a level gets the same wire length T_l and the same repeater count; short
  edges take a legal detour through repeater waypoints so that every segment is a SHORTEST legal maze path
  (GRT cannot shortcut).  Same cell chain on every root->leaf path by construction.
* Sites: bottom-up minimax on legal maze distance (leaf driver = leaf-group centroid; parents = legal cell
  minimising the max maze distance to their children).  Optional fixed island list (master plan) replaces
  the computed level-2 sites.  Node keep-out bands (e.g. the crowded SRAM-CK column) are honoured.
* Model (plan-only, no measured input): ASAP7 NLDM + Elmore per point-to-point net, leaf nets as MST with
  per-edge downstream C; SHARED-WIRE ACCOUNTING: per net, sum(branch path lengths) - union(path cells);
  per gcell clock-track demand of all planned paths.  Also emits a synthetic clock netlist + SPEF for an
  OpenSTA dmp_ceff_elmore check (core_infra_sta convention: 0 ps source slew unless declared).
No CTS balancing, no pads, no measured timing input.  Output Tcl uses the R5 ot_ms_* spec format.
"""
import argparse, collections, json, math, sys
from pathlib import Path

REP = 'BUFx16f_ASAP7_75t_R'
BIG = 'BUFx24_ASAP7_75t_R'
FFC = {'TT': 0.474736, 'FF': 0.522010}   # DFFHQNx1 CLK pin C per corner (actual liberty)


# ---------------------------------------------------------------- liberty
def lib_cells(path, names):
    import re
    t = open(path).read(); out = {}
    for n in names:
        i = t.find('cell (%s)' % n)
        if i < 0: i = t.find('cell ("%s")' % n)
        j = t.find('\n  cell (', i + 10); blk = t[i:j if j > 0 else None]
        cap = float(re.search(r'pin \(A\)\s*\{[^}]*?capacitance : ([\d.]+)', blk, re.S).group(1))
        def tab(kind):
            m = re.search(kind + r' \(\w+\) \{\s*index_1 \("([^"]+)"\);\s*index_2 \("([^"]+)"\);\s*values \((.*?)\);', blk, re.S)
            return ([float(x) for x in m.group(1).split(',')], [float(x) for x in m.group(2).split(',')],
                    [[float(x) for x in r.split(',')] for r in re.findall(r'"([^"]+)"', m.group(3))])
        out[n] = dict(cin=cap, rise=tab('cell_rise'), fall=tab('cell_fall'), trise=tab('rise_transition'), tfall=tab('fall_transition'))
    return out


def interp(tab, s, C):
    i1, i2, v = tab
    def idx(a, x):
        for k in range(len(a) - 1):
            if x <= a[k + 1]: return k
        return len(a) - 2
    a = idx(i1, s); b = idx(i2, C)
    ta = (s - i1[a]) / (i1[a + 1] - i1[a]); tb = (C - i2[b]) / (i2[b + 1] - i2[b])
    return v[a][b] * (1 - ta) * (1 - tb) + v[a + 1][b] * ta * (1 - tb) + v[a][b + 1] * (1 - ta) * tb + v[a + 1][b + 1] * ta * tb


# ---------------------------------------------------------------- geometry
class Maze:
    def __init__(self, core, macros, G=0.54, halo=2.2, keepout=()):
        self.core, self.G = core, G
        self.NX = int((core[2] - core[0]) / G); self.NY = int((core[3] - core[1]) / G)
        self.B = [[any(r[0] - halo < core[0] + i * G < r[2] + halo and r[1] - halo < core[1] + j * G < r[3] + halo for _, r, _ in macros)
                   for j in range(self.NY + 1)] for i in range(self.NX + 1)]
        # node keep-out (wires may pass, buffers may not sit): list of rects
        self.K = [[any(k[0] <= core[0] + i * G <= k[2] and k[1] <= core[1] + j * G <= k[3] for k in keepout)
                   for j in range(self.NY + 1)] for i in range(self.NX + 1)]
        self._bfs = {}

    def xy(self, c): return (round(self.core[0] + c[0] * self.G, 3), round(self.core[1] + c[1] * self.G, 3))

    def site_ok(self, i, j): return not self.B[i][j] and not self.K[i][j]

    def cell(self, p, node=True):
        i = min(self.NX, max(0, round((p[0] - self.core[0]) / self.G))); j = min(self.NY, max(0, round((p[1] - self.core[1]) / self.G)))
        ok = self.site_ok if node else (lambda a, b: not self.B[a][b])
        if ok(i, j): return (i, j)
        for r in range(1, 600):
            for di in range(-r, r + 1):
                for dj in (-r, r):
                    for a, b in ((i + di, j + dj), (i + dj, j + di)):
                        if 0 <= a <= self.NX and 0 <= b <= self.NY and ok(a, b): return (a, b)
        raise ValueError('no legal site near %s' % (p,))

    def bfs(self, c):
        if c in self._bfs: return self._bfs[c]
        NX, NY, B = self.NX, self.NY, self.B
        D = [[-1] * (NY + 1) for _ in range(NX + 1)]; D[c[0]][c[1]] = 0; q = collections.deque([c])
        while q:
            a, b = q.popleft(); d = D[a][b] + 1
            for na, nb in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                if 0 <= na <= NX and 0 <= nb <= NY and not B[na][nb] and D[na][nb] < 0:
                    D[na][nb] = d; q.append((na, nb))
        if len(self._bfs) > 400: self._bfs.clear()
        self._bfs[c] = D; return D

    def md(self, a, b): return self.bfs(a)[b[0]][b[1]] * self.G

    def path(self, a, b):
        """shortest legal cell path a->b, straight-preferring (fewest bends)."""
        D = self.bfs(b); out = [a]; c = a; last = None
        while c != b:
            a0, b0 = c; nb = [(a0 + 1, b0), (a0 - 1, b0), (a0, b0 + 1), (a0, b0 - 1)]
            if last is not None: nb.sort(key=lambda n: (n[0] - a0, n[1] - b0) != last)
            for n in nb:
                if 0 <= n[0] <= self.NX and 0 <= n[1] <= self.NY and D[n[0]][n[1]] == D[a0][b0] - 1:
                    last = (n[0] - a0, n[1] - b0); c = n; break
            out.append(c)
        return out


def balanced(points, centres, dist, iters=400):
    n = len(points); k = len(centres); tgt = [n // k + (1 if i < n % k else 0) for i in range(k)]
    Dm = [[dist(p, c) for c in centres] for p in points]; w = [0.0] * k
    for it in range(iters):
        a = [min(range(k), key=lambda c: Dm[i][c] + w[c]) for i in range(n)]; cnt = collections.Counter(a)
        if all(cnt[c] == tgt[c] for c in range(k)): break
        for c in range(k): w[c] += 0.5 * (cnt[c] - tgt[c]) / max(1, n / k) * 20 / (1 + it / 50)
    cnt = collections.Counter(a)
    while any(cnt[c] > tgt[c] for c in range(k)):
        best = None
        for i in range(n):
            if cnt[a[i]] <= tgt[a[i]]: continue
            for c in range(k):
                if cnt[c] < tgt[c]:
                    cost = Dm[i][c] - Dm[i][a[i]]
                    if best is None or cost < best[0]: best = (cost, i, c)
        _, i, c = best; cnt[a[i]] -= 1; cnt[c] += 1; a[i] = c
    return [[points[i] for i in range(n) if a[i] == c] for c in range(k)]


def split(pts, k, axis=None):
    """equal-count split into k groups (balanced k-means, Manhattan), seeded along the long axis."""
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    ax = axis if axis is not None else (0 if max(xs) - min(xs) > max(ys) - min(ys) else 1)
    srt = sorted(pts, key=lambda p: p[ax]); cs = [srt[int((i + .5) * len(srt) / k)][:2] for i in range(k)]
    for _ in range(6):
        grp = balanced(pts, list(range(k)), lambda s, c: abs(s[0] - cs[c][0]) + abs(s[1] - cs[c][1]), iters=300)
        cs = [(sorted(p[0] for p in g)[len(g) // 2], sorted(p[1] for p in g)[len(g) // 2]) for g in grp]
    return grp


def minimax_site(mz, children, around, radius=90, step=2):
    for c in children: mz.bfs(c)
    i0, j0 = around; best = None
    for i in range(max(0, i0 - radius), min(mz.NX, i0 + radius) + 1, step):
        for j in range(max(0, j0 - radius), min(mz.NY, j0 + radius) + 1, step):
            if not mz.site_ok(i, j): continue
            ds = [mz.bfs(c)[i][j] for c in children]
            if min(ds) < 0: continue
            v = (max(ds), sum(ds))
            if best is None or v < best[0]: best = (v, (i, j))
    return best[1]


def exact_points(mz, a, b, T, k):
    """k-1 repeater cells on exact shortest-path waypoints so the chain a->...->b has total legal length T
    (each segment a SHORTEST legal path, so GRT cannot shortcut the pad).  Waypoint i minimises
    |D_prev(p) - T/k| + |D_b(p) - remaining| over legal node sites (full-grid search)."""
    if k == 1: return []
    t = round(T / mz.G); Db = mz.bfs(b); NX, NY = mz.NX, mz.NY
    pts = []; p = a; done = 0
    for i in range(k - 1):
        seg = round((t - done) / (k - i)); remain = t - done - seg
        Dp = mz.bfs(p); best = None
        for x in range(NX + 1):
            Dx = Dp[x]; Dbx = Db[x]
            for y in range(NY + 1):
                if Dx[y] < 0 or Dbx[y] < 0: continue
                e = (abs(Dx[y] + Dbx[y] - (t - done)), abs(Dx[y] - seg))
                if (best is None or e < best[0]) and mz.site_ok(x, y): best = (e, (x, y), Dx[y])
        e, q, dq = best; e = e[0]
        if e > 2: print('WARN exact', a, b, round(T, 2), k, i, round(e * mz.G, 2), file=sys.stderr)
        pts.append(q); done += dq; p = q
    return pts


# ---------------------------------------------------------------- planner
def plan(geo, splits, smax, keepout, islands=None, macro_leaf=True):
    sinks = []; macros = []
    for l in open(geo):
        f = l.split()
        if not f: continue
        if f[0] == 'CORE': core = tuple(map(float, f[1:5]))
        if f[0] == 'PIN' and f[1] == 'ck': entry = (float(f[2]), float(f[3]))
        if f[0] == 'SINK': sinks.append((float(f[1]), float(f[2]), f[4], f[5], f[3]))
        if f[0] == 'MACRO': macros.append((f[1], tuple(map(float, f[3:7])), (float(f[8]), float(f[9]))))
    mz = Maze(core, macros, keepout=keepout)
    ent = mz.cell(entry, node=False)
    # ---- recursive equal-count partition (level 1 split on x = W/E about the entry)
    groups = {(): sinks}; order = [()]
    if islands is not None:
        # equal-count maze power diagram over the 4 given islands; side = island side of the entry
        isl = [mz.cell(p) for p in islands]
        for c_ in isl: mz.bfs(c_)
        sc = {s: mz.cell(s[:2], node=False) for s in sinks}
        Q = balanced(sinks, isl, lambda s, c_: mz.md(c_, sc[s]))
        W = [i for i in range(4) if mz.xy(isl[i])[0] < entry[0]]; E = [i for i in range(4) if i not in W]
        assert len(W) == 2 and len(E) == 2, 'need 2 islands per side'
        quad = {0: [Q[i] for i in W], 1: [Q[i] for i in E]}; isl_of = {(0, 0): isl[W[0]], (0, 1): isl[W[1]], (1, 0): isl[E[0]], (1, 1): isl[E[1]]}
        groups[(0,)] = Q[W[0]] + Q[W[1]]; groups[(1,)] = Q[E[0]] + Q[E[1]]
    for lv, k in enumerate(splits):
        if lv == 0 and islands is not None: continue
        new = {}
        for key in [g for g in groups if len(g) == lv]:
            pts = groups[key]
            if lv == 0 and k == 2:
                srt = sorted(pts, key=lambda p: (p[0], p[1])); h = len(srt) // 2; parts = [srt[:h], srt[h:]]
            elif lv == 1 and islands is not None:
                parts = quad[key[0]]
            else:
                parts = split(pts, k, axis=(1 if lv == 1 else None))
            for i, g in enumerate(parts): new[key + (i,)] = g
        groups.update(new)
    depth = len(splits)
    leaves = sorted(g for g in groups if len(g) == depth)
    site = {}
    for g in leaves:
        pts = groups[g]; site[g] = mz.cell((sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)))
    for lv in range(depth - 1, 0, -1):
        for g in sorted(x for x in groups if len(x) == lv):
            ch = [site[g + (i,)] for i in range(splits[lv])]
            if lv == 2 and islands is not None:
                pass
            if lv == 2 and islands is not None: site[g] = isl_of[g]; continue
            if lv == 2 and islands is None: pass
            cx = round(sum(c[0] for c in ch) / len(ch)); cy = round(sum(c[1] for c in ch) / len(ch))
            if lv == 1 and islands is not None:
                ch = [isl_of[g + (i,)] for i in range(2)]; cx = round(sum(c[0] for c in ch) / 2); cy = round(sum(c[1] for c in ch) / 2)
                # side hub: minimise max(entry->hub + hub->island) i.e. on the entry->island shortest paths
                for c_ in ch + [ent]: mz.bfs(c_)
                best = None
                for i in range(mz.NX + 1):
                    for j in range(0, mz.NY + 1, 1):
                        if not mz.site_ok(i, j): continue
                        de = mz.bfs(ent)[i][j]
                        if de < 0 or (mz.xy((i, j))[0] < entry[0]) != (g[0] == 0): continue
                        ds = [mz.bfs(c_)[i][j] for c_ in ch]
                        if min(ds) < 0: continue
                        v = (de + max(ds), max(ds), de)
                        if best is None or v < best[0]: best = (v, (i, j))
                site[g] = best[1]; continue
            site[g] = minimax_site(mz, ch, (cx, cy))
        if lv == 2 and islands is not None:
            isl = [mz.cell(p) for p in islands]
            for g in sorted(x for x in groups if len(x) == 2):
                # pin the given island to this group (nearest unused in the same side)
                pass
    site[()] = ent
    # ---- equal level lengths
    T = []; K = []
    for lv in range(depth):
        L = [mz.md(site[g[:-1]], site[g]) for g in groups if len(g) == lv + 1]
        T.append(max(L)); K.append(max(1, math.ceil(max(L) / smax)))
    nodes = []; wires = []   # nodes: (name, parent, cell, master, kind)
    def nm(g): return 'R' if not g else 'T' + ''.join(str(i) for i in g)
    nodes.append(('root', None, ent, BIG, 'entry'))
    branch_of = {(): 'root'}
    for lv in range(depth):
        for g in sorted(x for x in groups if len(x) == lv + 1):
            par = g[:-1]; pc = site[par]; cc = site[g]
            # branch buffer co-located at parent (offset 1.08 um per sibling, legal), driving ONE wire
            bname = nm(g) + '_br'
            off = mz.cell((mz.xy(pc)[0], mz.xy(pc)[1] + (g[-1] - (splits[lv] - 1) / 2) * 1.08))
            nodes.append((bname, branch_of[par], off, BIG if lv < depth - 1 else BIG, 'branch'))
            pts = exact_points(mz, off, cc, T[lv], K[lv]); prev = bname; chain = [off] + pts + [cc]
            for i, c in enumerate(pts):
                n = nm(g) + '_r%d' % i; nodes.append((n, prev, c, REP, 'rep')); prev = n
            wires.append(dict(level=lv + 1, edge=nm(g), segs=[mz.md(chain[i], chain[i + 1]) for i in range(len(chain) - 1)],
                              cells=[mz.path(chain[i], chain[i + 1]) for i in range(len(chain) - 1)]))
            if lv == depth - 1:
                nodes.append((nm(g), prev, cc, BIG, 'leaf'))
            else:
                nodes.append((nm(g), prev, cc, BIG, 'node'))
            branch_of[g] = nm(g)
    # nodes now: node buffers drive the local fan to their branch buffers.  For R6 the node buffer itself is
    # kept (one stage) only at the entry; at interior nodes the wire lands directly on the branch buffers.
    named = {n[0]: n for n in nodes}
    fold = {}
    for n in nodes:
        if n[4] == 'node': fold[n[0]] = n[1]   # interior node buffer removed: children hang on its driver
    # landing: the last driver of an edge whose node was folded drives ONE wire (last segment) to a hub at
    # the node site; the next level's co-located branch buffers hang on that hub by <=2 um stubs.
    land = {}
    for w in wires:
        if w['edge'] in fold: land[fold[w['edge']]] = (w['segs'][-1], w['edge'])
    final = []
    for n in nodes:
        if n[0] in fold: continue
        par = n[1]
        while par in fold: par = fold[par]
        final.append((n[0], par, n[2], n[3], n[4]))
    leafsinks = {nm(g): groups[g] for g in leaves}
    mac = []
    if macro_leaf:
        for name, rect, ck in macros:
            c = mz.cell((ck[0] + 2.2, ck[1])); lf = min(leaves, key=lambda g: mz.md(site[g], c))
            mac.append((name, nm(lf), c))
    return dict(mz=mz, entry=entry, ent=ent, groups=groups, leaves=leaves, site=site, T=T, K=K, nodes=final,
                wires=wires, land=land, leafsinks=leafsinks, macros=mac, splits=splits, nm=nm)


# ---------------------------------------------------------------- model
def mst_edges(pts):
    n = len(pts); inn = [False] * n; dd = [1e18] * n; par = [-1] * n; dd[0] = 0; order = []
    for _ in range(n):
        u = min((i for i in range(n) if not inn[i]), key=lambda i: dd[i]); inn[u] = True; order.append(u)
        for v in range(n):
            if not inn[v]:
                e = abs(pts[u][0] - pts[v][0]) + abs(pts[u][1] - pts[v][1])
                if e < dd[v]: dd[v] = e; par[v] = u
    return par, order


def model(P, libs, r, c, src_slew=0.0, ffc=FFC, allow_star=False):
    """allow_star: comparison mode for legacy multi-branch nets (star, no shared-trunk term)."""
    mz = P['mz']; nodes = P['nodes']; ch = collections.defaultdict(list)
    for n in nodes:
        if n[1]: ch[n[1]].append(n)
    pos = {n[0]: mz.xy(n[2]) for n in nodes}
    wirelen = {}   # child name -> planned wire length from its driver (maze segment)
    for w in P['wires']:
        e = w['edge']; segs = w['segs']
        names = [e + '_br'] + [e + '_r%d' % i for i in range(len(segs) - 1)] + [e]
        for i in range(len(segs)):
            wirelen[names[i + 1]] = segs[i]
    pos_hub = {w['edge']: mz.xy(w['cells'][-1][-1]) for w in P['wires']}
    res = {}
    for corner, L in libs.items():
        arr = {'root': 0.0}; slew = {'root': src_slew}; leafarr = {}
        stack = ['root']
        while stack:
            u = stack.pop(); kids = ch.get(u, []); master = [n for n in nodes if n[0] == u][0][3]
            lib = L[master]
            if kids:
                # each kid at its planned wire (maze) length; co-located kids share a <=2 um local fan
                if u in P['land']:
                    seg, hub = P['land'][u]; hp = pos_hub[hub]
                    stub = [abs(pos[k[0]][0] - hp[0]) + abs(pos[k[0]][1] - hp[1]) for k in kids]
                    if max(stub) > 4.0: raise ValueError('hub stub too long at ' + u)
                    Cl = sum(L[k[3]]['cin'] for k in kids) + c * sum(stub); Ct = c * seg + Cl
                    d = 0.5 * (interp(lib['rise'], slew[u], Ct) + interp(lib['fall'], slew[u], Ct))
                    so = 0.5 * (interp(lib['trise'], slew[u], Ct) + interp(lib['tfall'], slew[u], Ct))
                    el = r * seg * (c * seg / 2 + Cl)
                    for k, sl_ in zip(kids, stub):
                        e2 = el + r * sl_ * L[k[3]]['cin']
                        arr[k[0]] = arr[u] + d + e2; slew[k[0]] = math.hypot(so, 2.2 * e2); stack.append(k[0])
                    kids = []
            if kids:
                br = [(wirelen.get(k[0], abs(pos[k[0]][0] - pos[u][0]) + abs(pos[k[0]][1] - pos[u][1])), L[k[3]]['cin']) for k in kids]
                local = [b for b in br if b[0] < 3.0]; far = [b for b in br if b[0] >= 3.0]
                if far and local: raise ValueError('mixed local/far fan at ' + u)
                if far:
                    if len(far) > 1 and not allow_star: raise ValueError('shared wire: %s drives %d far branches' % (u, len(far)))
                    Ct = sum(c * b[0] + b[1] for b in far) + sum(c * b[0] + b[1] for b in local)
                else:
                    Ct = c * (sum(b[0] for b in local) + 0.0) + sum(b[1] for b in local)
                d = 0.5 * (interp(lib['rise'], slew[u], Ct) + interp(lib['fall'], slew[u], Ct))
                so = 0.5 * (interp(lib['trise'], slew[u], Ct) + interp(lib['tfall'], slew[u], Ct))
                for (w, cp), k in zip(br, kids):
                    el = r * w * (c * w / 2 + cp)
                    arr[k[0]] = arr[u] + d + el; slew[k[0]] = math.hypot(so, 2.2 * el); stack.append(k[0])
            if u in P['leafsinks']:
                ls = P['leafsinks'][u]; pts = [pos[u]] + [s[:2] for s in ls]
                par, order = mst_edges(pts); sub = [0.0] + [ffc[corner] for _ in ls]; ec = [0.0] * len(pts); er = [0.0] * len(pts)
                for v in order[1:]:
                    e = abs(pts[v][0] - pts[par[v]][0]) + abs(pts[v][1] - pts[par[v]][1]); ec[v] = c * e; er[v] = r * e
                for v in reversed(order[1:]): sub[par[v]] += sub[v] + ec[v]
                Ct = sub[0]
                d = 0.5 * (interp(lib['rise'], slew[u], Ct) + interp(lib['fall'], slew[u], Ct))
                t = [0.0] * len(pts)
                for v in order[1:]: t[v] = t[par[v]] + er[v] * (sub[v] - ec[v] / 2)
                vals = [arr[u] + d + x for x in t[1:]]
                leafarr[u] = (sum(vals) / len(vals), min(vals), max(vals), Ct, sum(ec))
        means = [v[0] for v in leafarr.values()]; allv = []
        for u, v in leafarr.items(): allv += [v[1], v[2]]
        n_s = sum(len(P['leafsinks'][u]) for u in leafarr)
        mean = sum(leafarr[u][0] * len(P['leafsinks'][u]) for u in leafarr) / n_s
        res[corner] = dict(mean=round(mean, 2), leaf_mean_min=round(min(means), 2), leaf_mean_max=round(max(means), 2),
                           window=round(max(means) - min(means), 2), sink_min=round(min(allv), 2), sink_max=round(max(allv), 2),
                           leaf={u: [round(x, 2) for x in v] for u, v in leafarr.items()})
    return res


def shared_wire(P):
    """per net: sum(branch lengths) - union length of the planned paths (0 => no shared trunk);
    per gcell (4.32 um): number of planned clock wires crossing it (track demand)."""
    mz = P['mz']; G = mz.G; per_net = collections.defaultdict(list)
    for w in P['wires']:
        per_net[w['edge'] + '_br'].append(w)
    shared = 0.0; worst = []
    demand = collections.Counter()
    for w in P['wires']:
        for cells in w['cells']:
            gc = set((int(mz.xy(c)[0] // 4.32), int(mz.xy(c)[1] // 4.32)) for c in cells)
            for g in gc: demand[g] += 1
    # each wire is driven by its own buffer: by construction 1 branch per net
    nets_multi = [k for k, v in per_net.items() if len(v) > 1]
    top = demand.most_common(8)
    return dict(nets_with_shared_branches=len(nets_multi), shared_um=round(shared, 2),
                max_clock_wires_per_gcell=top[0][1] if top else 0,
                hottest_gcells_um=[[round(g[0] * 4.32, 2), round(g[1] * 4.32, 2), n] for g, n in top])


# ---------------------------------------------------------------- outputs
def emit_tcl(P, out):
    mz = P['mz']; L = ['# core_infra_htree R6 equal-structure H-tree, buffer at every branch point (plan-computed, no measurement input)',
                       'set ot_ms_port ck', 'set ot_ms_root {%.3f %.3f}' % mz.xy(P['ent']), 'set ot_h_entry_n 0', 'set ot_h_fixed {']
    # FIRM pushdown cells (12.2a1): the entry root + the branch buffers sitting at each island hub
    isl_xy = set(mz.xy(P['site'][g]) for g in P.get('isl_groups', []))
    # one FIRM cell per island (the first island branch buffer); co-located siblings are DPL-legalised next to it
    first = set(P['nm'](g + (0,)) + '_br' for g in P.get('isl_groups', []))
    def at_island(n): return n[0] in first
    fixed = [n for n in P['nodes'] if n[4] == 'entry'] + [n for n in P['nodes'] if at_island(n)]
    L += [' {%s %s %.3f %.3f}' % ('ot_ms_root' if n[0] == 'root' else 'ot_ms_' + n[0] + '_nd', n[3], *mz.xy(n[2])) for n in fixed] + ['}', 'set ot_ms_tree {']
    L += [' {%s %s %.3f %.3f %s}' % (n[0], n[1], *mz.xy(n[2]), n[3]) for n in P['nodes'] if n[4] in ('branch', 'rep')] + ['}', 'set ot_ms_leaves {']
    q = lambda s: '{' + s + '}'
    for n in P['nodes']:
        if n[4] != 'leaf': continue
        ls = P['leafsinks'][n[0]]
        L.append(' {%s %s {%.3f %.3f} {%s} %s}' % (n[0], n[1], *mz.xy(n[2]), ' '.join('{' + q(s[2]) + ' ' + q(s[3]) + '}' for s in ls), n[3]))
    L += ['}', 'set ot_ms_macros {'] + [' {%s %s {%.3f %.3f}}' % (q(a), b, *mz.xy(c)) for a, b, c in P['macros']] + ['}']
    Path(out).write_text('\n'.join(L) + '\n')


def emit_sta(P, outdir, r, c, ffmaster=None):
    """synthetic clock netlist + SPEF (planned maze lengths, distributed 2-pin wires, MST leaf nets)."""
    out = Path(outdir); out.mkdir(parents=True, exist_ok=True); mz = P['mz']; nodes = P['nodes']
    pos = {n[0]: mz.xy(n[2]) for n in nodes}; ch = collections.defaultdict(list)
    for n in nodes:
        if n[1]: ch[n[1]].append(n)
    wirelen = {}
    for w in P['wires']:
        e = w['edge']; segs = w['segs']; names = [e + '_br'] + [e + '_r%d' % i for i in range(len(segs) - 1)] + [e]
        for i in range(len(segs)): wirelen[names[i + 1]] = segs[i]
    al = {n[0]: 'b%d' % i for i, n in enumerate(nodes)}; net = {n[0]: 'n%d' % i for i, n in enumerate(nodes)}
    sinks = []
    for u, ls in P['leafsinks'].items():
        for s in ls: sinks.append((u, s))
    v = ['module clock_plan_model(input ck, output [%d:0] q);' % (len(sinks) - 1), 'wire ' + ', '.join(net.values()) + ';']
    for n in nodes:
        v.append('%s %s (.A(%s), .Y(%s));' % (n[3], al[n[0]], 'ck' if n[1] is None else net[n[1]], net[n[0]]))
    for i, (u, s) in enumerate(sinks):
        m = s[4]
        if m.startswith('DFFLQN'): pins = '.CLK(%s), .D(1\'b0), .QN(q[%d])'
        elif m.startswith('DFFASRHQN'): pins = '.CLK(%s), .D(1\'b0), .RESETN(1\'b1), .SETN(1\'b1), .QN(q[%d])'
        else: pins = '.CLK(%s), .D(1\'b0), .QN(q[%d])'
        v.append('%s f%d (%s);' % (m, i, pins % (net[u], i)))
    v.append('endmodule'); (out / 'model.v').write_text('\n'.join(v) + '\n')
    sp = ['*SPEF "IEEE 1481-1998"', '*DESIGN "clock_plan_model"', '*DATE "PLAN ONLY"', '*VENDOR "OpenTallas"', '*PROGRAM "core_infra_htree"',
          '*VERSION "1"', '*DESIGN_FLOW "PIN_CAP NONE"', '*DIVIDER /', '*DELIMITER :', '*BUS_DELIMITER [ ]', '*T_UNIT 1 PS', '*C_UNIT 1 FF', '*R_UNIT 1 KOHM', '*L_UNIT 1 HENRY']
    def ladder(name, drv, tgts):  # tgts: (pin, length)
        caps = []; ress = []; k = [0]
        def nid(): k[0] += 1; return '%s:%d' % (name, k[0])
        root = nid(); ress.append((drv, root, 1e-6))
        for pin, ln in tgts:
            nseg = max(1, int(math.ceil(ln / 5.0))); prev = root
            for s in range(nseg):
                x = nid(); ress.append((prev, x, r * ln / nseg)); caps.append((x, c * ln / nseg)); prev = x
            ress.append((prev, pin, 1e-6))
        tot = sum(cc for _, cc in caps)
        sp.extend(['*D_NET %s %.6g' % (name, tot), '*CONN', ('*P ' if drv == 'ck' else '*I ') + drv + (' I' if drv == 'ck' else ' O')]
                  + ['*I %s I' % p for p, _ in tgts] + ['*CAP'] + ['%d %s %.6g' % (i + 1, a, b) for i, (a, b) in enumerate(caps)]
                  + ['*RES'] + ['%d %s %s %.6g' % (i + 1, a, b, cc) for i, (a, b, cc) in enumerate(ress)] + ['*END'])
    ladder('ck', 'ck', [(al['root'] + ':A', 0.5)])
    sidx = {id(s): i for i, (u, s) in enumerate(sinks)}
    pos_hub = {w['edge']: mz.xy(w['cells'][-1][-1]) for w in P['wires']}
    for n in nodes:
        u = n[0]; tg = [(al[k[0]] + ':A', max(0.2, wirelen.get(k[0], abs(pos[k[0]][0] - pos[u][0]) + abs(pos[k[0]][1] - pos[u][1])))) for k in ch.get(u, [])]
        if u in P['leafsinks']:
            # MST tree net
            ls = P['leafsinks'][u]; pts = [pos[u]] + [s[:2] for s in ls]; par, order = mst_edges(pts)
            caps = []; ress = [(al[u] + ':Y', '%s:0' % net[u], 1e-6)]
            for vv in order[1:]:
                e = max(0.1, abs(pts[vv][0] - pts[par[vv]][0]) + abs(pts[vv][1] - pts[par[vv]][1]))
                ress.append(('%s:%d' % (net[u], par[vv]), '%s:%d' % (net[u], vv), r * e)); caps.append(('%s:%d' % (net[u], vv), c * e))
                ress.append(('%s:%d' % (net[u], vv), 'f%d:CLK' % sidx[id(ls[vv - 1])], 1e-6))
            sp.extend(['*D_NET %s %.6g' % (net[u], sum(x for _, x in caps)), '*CONN', '*I %s:Y O' % al[u]] + ['*I f%d:CLK I' % sidx[id(s)] for s in ls]
                      + ['*CAP'] + ['%d %s %.6g' % (i + 1, a, b) for i, (a, b) in enumerate(caps)] + ['*RES']
                      + ['%d %s %s %.6g' % (i + 1, a, b, x) for i, (a, b, x) in enumerate(ress)] + ['*END'])
        elif u in P['land']:
            seg, hub = P['land'][u]; hp = pos_hub[hub]; kids = ch.get(u, [])
            caps = []; ress = [(al[u] + ':Y', '%s:0' % net[u], 1e-6)]; nseg = max(1, int(math.ceil(seg / 5.0)))
            for s_ in range(nseg):
                ress.append(('%s:%d' % (net[u], s_), '%s:%d' % (net[u], s_ + 1), r * seg / nseg)); caps.append(('%s:%d' % (net[u], s_ + 1), c * seg / nseg))
            for i, k in enumerate(kids):
                e = max(0.1, abs(pos[k[0]][0] - hp[0]) + abs(pos[k[0]][1] - hp[1])); x = '%s:%d' % (net[u], 100000 + i)
                ress.append(('%s:%d' % (net[u], nseg), x, r * e)); caps.append((x, c * e)); ress.append((x, al[k[0]] + ':A', 1e-6))
            sp.extend(['*D_NET %s %.6g' % (net[u], sum(x for _, x in caps)), '*CONN', '*I %s:Y O' % al[u]] + ['*I %s:A I' % al[k[0]] for k in kids]
                      + ['*CAP'] + ['%d %s %.6g' % (i + 1, a, b) for i, (a, b) in enumerate(caps)] + ['*RES']
                      + ['%d %s %s %.6g' % (i + 1, a, b, x) for i, (a, b, x) in enumerate(ress)] + ['*END'])
        elif tg:
            ladder(net[u], al[u] + ':Y', tg)
    (out / 'plan.spef').write_text('\n'.join(sp) + '\n')
    leafof = {}
    for i, (u, s) in enumerate(sinks): leafof['f%d' % i] = u
    (out / 'leafof.json').write_text(json.dumps(leafof))
    tcl = ['set c $::env(CORNER)', 'set P /OpenROAD-flow-scripts/flow/platforms/asap7', 'read_lef $P/lef/asap7_tech_1x_201209.lef',
           'read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef', 'foreach f [glob $P/lib/NLDM/*_RVT_${c}_*] {read_liberty $f}',
           'read_verilog /work/model.v', 'link_design clock_plan_model', 'create_clock -name core -period 833 [get_ports ck]',
           'set_clock_transition 0 [get_clocks core]', 'set_delay_calculator dmp_ceff_elmore', 'read_spef /work/plan.spef',
           'set_propagated_clock [all_clocks]', 'report_worst_slack -max', 'set f [open /work/arrivals_${c}.tsv w]',
           'foreach p [get_pins f*/CLK] {puts $f "[get_full_name $p]\\t[get_property $p arrival_max_rise]"}', 'close $f', 'puts PLAN_STA_DONE']
    (out / 'model.tcl').write_text('\n'.join(tcl) + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('geo'); ap.add_argument('out')
    ap.add_argument('--libtt', required=True); ap.add_argument('--libff', required=True)
    ap.add_argument('--splits', default='2,2,4,4'); ap.add_argument('--smax', type=float, default=70.0)
    ap.add_argument('--keepout', action='append', default=[], help='x0,y0,x1,y1 node keep-out')
    ap.add_argument('--islands', default=None, help='x,y;x,y;... fixed level-2 island sites (master plan)')
    ap.add_argument('--rc', default='0.8,0.9'); ap.add_argument('--src-slew', type=float, default=0.0)
    ap.add_argument('--sta-dir', default=None)
    ap.add_argument('--nb', default=None, help='B fanout per island (order of --islands), selects the R6 ring planner')
    ap.add_argument('--leaf-n', type=int, default=4)
    ap.add_argument('--cap-balance', action='store_true', help='equal estimated C (pin + MST share) per group instead of equal count')
    ap.add_argument('--ring-islands', action='store_true', help='propose islands moved onto one maze ring about the entry')
    ap.add_argument('--r6', action='store_true'); ap.add_argument('--no-side-hub', action='store_true')
    a = ap.parse_args()
    keep = [tuple(map(float, k.split(','))) for k in a.keepout]
    isl = [tuple(map(float, p.split(','))) for p in a.islands.split(';')] if a.islands else None
    kr0, kc0 = map(float, a.rc.split(','))
    if a.r6:
        cw = None
        if a.cap_balance:
            _, _, _s, _ = read_geo(a.geo); cw = sink_weights(_s, 0.5 * (1.78475e-1 + 1.64264e-1) * kc0)
        P = plan_r6(a.geo, isl, [int(x) for x in a.nb.split(',')], a.leaf_n, not a.no_side_hub, a.smax, keepout=keep, cap_w=cw, ring_islands=a.ring_islands)
    elif a.nb: P = plan_ring(a.geo, isl, [int(x) for x in a.nb.split(',')], a.leaf_n, a.smax, keep)
    else: P = plan(a.geo, [int(x) for x in a.splits.split(',')], a.smax, keep, isl)
    kr, kc = map(float, a.rc.split(','))
    r = 0.5 * (1.80365e-2 + 1.89935e-2) * kr; c = 0.5 * (1.78475e-1 + 1.64264e-1) * kc
    libs = {'TT': lib_cells(a.libtt, [REP, BIG]), 'FF': lib_cells(a.libff, [REP, BIG])}
    pred = model(P, libs, r, c, a.src_slew)
    sw = shared_wire(P); mz = P['mz']
    emit_tcl(P, a.out)
    if a.sta_dir: emit_sta(P, a.sta_dir, r, c)
    stages = collections.Counter()
    leafs = [n for n in P['nodes'] if n[4] == 'leaf']; par = {n[0]: n[1] for n in P['nodes']}
    depths = set()
    for n in leafs:
        d = 1; u = n[0]
        while par[u]: u = par[u]; d += 1
        depths.add(d)
    rep = dict(scope='PLAN MODEL ONLY (ASAP7 NLDM + Elmore, setRC x rc_cal %s, src slew %.0f ps); UNCHECKED' % (a.rc, a.src_slew),
               entry=mz.xy(P['ent']), splits=P['splits'],
               sites={P['nm'](g): mz.xy(s) for g, s in P['site'].items()},
               entry_to_island_um={P['nm'](g): round(mz.md(P['ent'], P['site'][g]), 2) for g in P.get('isl_groups', [g for g in P['groups'] if len(g) == 2])},
               level_spread_um=P.get('level_spread_um'), islands_moved=P.get('islands_moved'),
               group_load={P['nm'](g): len(v) for g, v in P['groups'].items() if 0 < len(g) <= 2 and len(P['groups'][g]) > 400},
               leaf_load=[min(len(v) for v in P['leafsinks'].values()), max(len(v) for v in P['leafsinks'].values())],
               level_len_um=P['T'], repeaters_per_edge=[k - 1 for k in P['K']], stages_per_path=sorted(depths),
               path_wire_um=round(sum(P['T']), 2), level_range_um=P.get('level_range_um'),
               leaf_displacement_um=P.get('leaf_displacement_um'), b_displacement_um=P.get('b_displacement_um'), n_cells=len(P['nodes']) + len(P['macros']), shared_wire=sw,
               pred={k: {kk: vv for kk, vv in v.items() if kk != 'leaf'} for k, v in pred.items()}, pred_leaf=pred,
               nodes=[(n[0], n[1], mz.xy(n[2]), n[3], n[4]) for n in P['nodes']], macros=[(x, y, mz.xy(z)) for x, y, z in P['macros']])
    Path(a.out + '.json').write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: rep[k] for k in ('level_spread_um', 'level_range_um', 'leaf_displacement_um', 'b_displacement_um', 'entry_to_island_um', 'group_load', 'leaf_load', 'level_len_um', 'repeaters_per_edge', 'stages_per_path', 'path_wire_um', 'n_cells', 'shared_wire', 'pred')}, indent=0))



# ---------------------------------------------------------------- island search (proposal for the master plan)
def search_islands(geo, rmax=115.0, pitch=8.64, sample=6, G=1.08, passes=2, keepout=()):
    """Choose 2 W + 2 E island sites (4.32 lattice, legal, maze <= rmax from the entry) minimising
    max_q md(entry,I_q) + max_q P98(md(I_q, s in Q_q)) under an equal-count maze power-diagram assignment.
    Plan geometry only.  Returns sites + proxy numbers; the master plan adopts or re-sites."""
    sinks = []; macros = []
    for l in open(geo):
        f = l.split()
        if not f: continue
        if f[0] == 'CORE': core = tuple(map(float, f[1:5]))
        if f[0] == 'PIN' and f[1] == 'ck': entry = (float(f[2]), float(f[3]))
        if f[0] == 'SINK': sinks.append((float(f[1]), float(f[2])))
        if f[0] == 'MACRO': macros.append((f[1], tuple(map(float, f[3:7])), (float(f[8]), float(f[9]))))
    mz = Maze(core, macros, G=G, keepout=keepout); e = mz.cell(entry, node=False); De = mz.bfs(e)
    pts = sorted(sinks)[::sample]; pc = [mz.cell(p, node=False) for p in pts]
    cands = {0: [], 1: []}
    x = math.ceil(core[0] / 4.32) * 4.32
    while x < core[2]:
        y = math.ceil(core[1] / 4.32) * 4.32
        while y < core[3]:
            c = mz.cell((x, y)); 
            if mz.xy(c) == (round(x, 3), round(y, 3)) and 0 <= De[c[0]][c[1]] * G <= rmax:
                cands[0 if x < entry[0] else 1].append(c)
            y += pitch
        x += pitch
    dist = {}
    def D(c):
        if c not in dist:
            B = mz.bfs(c); dist[c] = [B[q[0]][q[1]] * G for q in pc]
        return dist[c]
    def evaluate(isl):
        ds = [D(c) for c in isl]
        grp = balanced(list(range(len(pts))), list(range(4)), lambda s, k: ds[k][s], iters=200)
        R = []
        for k, g in enumerate(grp):
            v = sorted(ds[k][s] for s in g); R.append(v[int(0.98 * (len(v) - 1))])
        t1 = max(De[c[0]][c[1]] * G for c in isl)
        return t1 + max(R), t1, R
    # init: per side, two candidates nearest the side's N/S sink medians
    isl = []
    for side in (0, 1):
        sp = [p for p in pts if (p[0] < entry[0]) == (side == 0)]
        for half in (0, 1):
            hp = [p for p in sp if (p[1] >= entry[1]) == (half == 0)] or sp
            m = (sorted(p[0] for p in hp)[len(hp) // 2], sorted(p[1] for p in hp)[len(hp) // 2])
            isl.append(min(cands[side], key=lambda c: abs(mz.xy(c)[0] - m[0]) + abs(mz.xy(c)[1] - m[1])))
    best = evaluate(isl)
    for _ in range(passes):
        for k in range(4):
            side = 0 if k < 2 else 1
            for c in cands[side]:
                if c in isl: continue
                trial = list(isl); trial[k] = c; v = evaluate(trial)
                if v[0] < best[0]: best, isl = v, trial
    return dict(entry=entry, islands=[mz.xy(c) for c in isl], proxy_um=round(best[0], 2), t1_um=round(best[1], 2),
                r98_um=[round(r, 2) for r in best[2]], entry_to_island_um=[round(De[c[0]][c[1]] * G, 2) for c in isl],
                candidates=[len(cands[0]), len(cands[1])], basis='plan geometry only: maze (macro+2.2 halo) distances, 1/%d sink sample' % sample)


# ---------------------------------------------------------------- R6 ring-equalised planner
def on_ring(mz, src, T, near, tol=1):
    """legal node site at maze distance T (+-tol cells) from src, nearest (maze from `near` if reachable) to near."""
    D = mz.bfs(src); t = round(T / mz.G); Dn = mz.bfs(near); best = None
    for i in range(mz.NX + 1):
        Di = D[i]; Dni = Dn[i]
        for j in range(mz.NY + 1):
            if Di[j] >= 0 and abs(Di[j] - t) <= tol and mz.site_ok(i, j) and Dni[j] >= 0:
                e = Dni[j]
                if best is None or e < best[0]: best = (e, (i, j))
    return best[1], best[0] * mz.G


def plan_ring(geo, islands, nb, leaf_n=4, smax=200.0, keepout=(), hub_ring=True):
    """entry -> W/E branch -> side hub -> 2 islands per side (given) -> nb[i] B per island -> leaf_n leaf drivers per B.
    Sites are top-down ring-equalised: every child of level l sits at EXACTLY maze distance T_l from its parent
    (T_l = max ideal distance of the level), nearest to its ideal site, so all edges of a level have the same
    shortest legal length without waypoint detours.  Leaf groups are equal-count (all leaves same load)."""
    sinks = []; macros = []
    for l in open(geo):
        f = l.split()
        if not f: continue
        if f[0] == 'CORE': core = tuple(map(float, f[1:5]))
        if f[0] == 'PIN' and f[1] == 'ck': entry = (float(f[2]), float(f[3]))
        if f[0] == 'SINK': sinks.append((float(f[1]), float(f[2]), f[4], f[5], f[3]))
        if f[0] == 'MACRO': macros.append((f[1], tuple(map(float, f[3:7])), (float(f[8]), float(f[9]))))
    mz = Maze(core, macros, keepout=keepout); ent = mz.cell(entry, node=False)
    isl = [mz.cell(p) for p in islands]; nleaf = sum(nb) * leaf_n
    for c_ in isl: mz.bfs(c_)
    sc = {s: mz.cell(s[:2], node=False) for s in sinks}
    # island capacity proportional to its leaf count; equal-count leaves
    n = len(sinks); tgt = [round(n * nb[i] * leaf_n / nleaf) for i in range(4)]; tgt[-1] = n - sum(tgt[:-1])
    Dm = [[mz.md(isl[k], sc[s]) for k in range(4)] for s in sinks]
    w = [0.0] * 4; a = None
    for it in range(600):
        a = [min(range(4), key=lambda k: Dm[i][k] + w[k]) for i in range(n)]; cnt = collections.Counter(a)
        if all(cnt[k] == tgt[k] for k in range(4)): break
        for k in range(4): w[k] += 0.5 * (cnt[k] - tgt[k]) / max(1, n / 4) * 20 / (1 + it / 50)
    cnt = collections.Counter(a)
    while any(cnt[k] > tgt[k] for k in range(4)):
        best = None
        for i in range(n):
            if cnt[a[i]] <= tgt[a[i]]: continue
            for k in range(4):
                if cnt[k] < tgt[k]:
                    cost = Dm[i][k] - Dm[i][a[i]]
                    if best is None or cost < best[0]: best = (cost, i, k)
        _, i, k = best; cnt[a[i]] -= 1; cnt[k] += 1; a[i] = k
    Q = [[sinks[i] for i in range(n) if a[i] == k] for k in range(4)]
    W = sorted([k for k in range(4) if mz.xy(isl[k])[0] < entry[0]]); E = sorted(k for k in range(4) if k not in W)
    assert len(W) == 2 and len(E) == 2, 'need 2 islands per side'
    groups = {(): sinks}; site = {(): ent}; ideal = {}
    order = [(0, 0, W[0]), (0, 1, W[1]), (1, 0, E[0]), (1, 1, E[1])]
    for s_, h, k in order:
        groups[(s_, h)] = Q[k]; site[(s_, h)] = isl[k]
    groups[(0,)] = Q[W[0]] + Q[W[1]]; groups[(1,)] = Q[E[0]] + Q[E[1]]
    for s_, h, k in order:
        for bi, bg in enumerate(split(Q[k], nb[k])):
            groups[(s_, h, bi)] = bg
            for li, lg in enumerate(split(bg, leaf_n)): groups[(s_, h, bi, li)] = lg
    for g, pts in groups.items():
        if len(g) == 4: ideal[g] = mz.cell((sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)))
    for g in [x for x in groups if len(x) == 3]:
        ch = [ideal[g + (i,)] for i in range(leaf_n)]
        ideal[g] = minimax_site(mz, ch, (round(sum(c[0] for c in ch) / leaf_n), round(sum(c[1] for c in ch) / leaf_n)))
    # side hubs: equal distance to both islands of the side and to the entry across both sides
    best = None
    for i in range(mz.NX + 1):
        for j in range(mz.NY + 1):
            pass
    hubs = {}
    De = mz.bfs(ent)
    for s_ in (0, 1):
        I2 = [site[(s_, 0)], site[(s_, 1)]]; D0 = mz.bfs(I2[0]); D1 = mz.bfs(I2[1]); b = None
        for i in range(mz.NX + 1):
            for j in range(mz.NY + 1):
                if not mz.site_ok(i, j) or De[i][j] < 0 or D0[i][j] < 0 or D1[i][j] < 0: continue
                if (mz.xy((i, j))[0] < entry[0]) != (s_ == 0): continue
                v = (De[i][j] + max(D0[i][j], D1[i][j]), abs(D0[i][j] - D1[i][j]), -De[i][j])
                if b is None or v < b[0]: b = (v, (i, j))
        hubs[s_] = b[1]
    for s_ in (0, 1): site[(s_,)] = hubs[s_]
    T1 = max(mz.md(ent, hubs[s_]) for s_ in (0, 1)); T2 = max(mz.md(hubs[s_], site[(s_, h)]) for s_ in (0, 1) for h in (0, 1))
    T3 = max(mz.md(site[g[:2]], ideal[g]) for g in groups if len(g) == 3)
    disp = {}
    for g in sorted(x for x in groups if len(x) == 3):
        site[g], disp[g] = on_ring(mz, site[g[:2]], T3, ideal[g])
    T4 = max(mz.md(site[g[:3]], ideal[g]) for g in groups if len(g) == 4)
    for g in sorted(x for x in groups if len(x) == 4):
        site[g], disp[g] = on_ring(mz, site[g[:3]], T4, ideal[g])
    T = [T1, T2, T3, T4]; K = [max(1, math.ceil(t / smax)) for t in T]
    def nm(g): return 'R' if not g else 'T' + ''.join(str(i) for i in g)
    nodes = [('root', None, ent, BIG, 'entry')]; wires = []; last = {(): 'root'}; land = {}
    for lv in range(4):
        for g in sorted(x for x in groups if len(x) == lv + 1):
            par = g[:-1]; pc = site[par]; nsib = len([x for x in groups if len(x) == lv + 1 and x[:-1] == par])
            off = mz.cell((mz.xy(pc)[0], mz.xy(pc)[1] + (g[-1] - (nsib - 1) / 2) * 1.08))
            bname = nm(g) + '_br'; nodes.append((bname, last[par], off, BIG, 'branch'))
            pts = exact_points(mz, off, site[g], mz.md(off, site[g]), K[lv]); prev = bname; chain = [off] + pts + [site[g]]
            for i, c in enumerate(pts):
                nn = nm(g) + '_r%d' % i; nodes.append((nn, prev, c, REP, 'rep')); prev = nn
            segs = [mz.md(chain[i], chain[i + 1]) for i in range(len(chain) - 1)]
            wires.append(dict(level=lv + 1, edge=nm(g), segs=segs, cells=[mz.path(chain[i], chain[i + 1]) for i in range(len(chain) - 1)]))
            if lv == 3: nodes.append((nm(g), prev, site[g], BIG, 'leaf'))
            else: land[prev] = (segs[-1], nm(g))
            last[g] = prev
    leaves = sorted(x for x in groups if len(x) == 4)
    leafsinks = {nm(g): groups[g] for g in leaves}
    mac = []
    for name, rect, ck in macros:
        c = mz.cell((ck[0] + 2.2, ck[1])); lf = min(leaves, key=lambda g: mz.md(site[g], c)); mac.append((name, nm(lf), c))
    lvl = collections.defaultdict(list)
    for w_ in wires: lvl[w_['level']].append(sum(w_['segs']))
    return dict(mz=mz, entry=entry, ent=ent, groups=groups, leaves=leaves, site=site, T=T, K=K, nodes=nodes, wires=wires, land=land,
                leafsinks=leafsinks, macros=mac, splits=[2, 2, nb, leaf_n], nm=nm,
                level_range_um={l: [round(min(v), 2), round(max(v), 2)] for l, v in lvl.items()},
                leaf_displacement_um=[round(min(v for g, v in disp.items() if len(g) == 4), 2), round(max(v for g, v in disp.items() if len(g) == 4), 2)],
                b_displacement_um=[round(min(v for g, v in disp.items() if len(g) == 3), 2), round(max(v for g, v in disp.items() if len(g) == 3), 2)])



# ---------------------------------------------------------------- R6 planner (padded levels, given islands)
def read_geo(geo):
    sinks = []; macros = []
    for l in open(geo):
        f = l.split()
        if not f: continue
        if f[0] == 'CORE': core = tuple(map(float, f[1:5]))
        if f[0] == 'PIN' and f[1] == 'ck': entry = (float(f[2]), float(f[3]))
        if f[0] == 'SINK': sinks.append((float(f[1]), float(f[2]), f[4], f[5], f[3]))
        if f[0] == 'MACRO': macros.append((f[1], tuple(map(float, f[3:7])), (float(f[8]), float(f[9]))))
    return core, entry, sinks, macros


def assign(mz, sinks, centres, targets, iters=600):
    sc = {s: mz.cell(s[:2], node=False) for s in sinks}
    for c_ in centres: mz.bfs(c_)
    n = len(sinks); k = len(centres); Dm = [[mz.md(centres[j], sc[s]) for j in range(k)] for s in sinks]; w = [0.0] * k
    for it in range(iters):
        a = [min(range(k), key=lambda j: Dm[i][j] + w[j]) for i in range(n)]; cnt = collections.Counter(a)
        if all(cnt[j] == targets[j] for j in range(k)): break
        for j in range(k): w[j] += 0.5 * (cnt[j] - targets[j]) / max(1, n / k) * 20 / (1 + it / 50)
    cnt = collections.Counter(a)
    while any(cnt[j] > targets[j] for j in range(k)):
        best = None
        for i in range(n):
            if cnt[a[i]] <= targets[a[i]]: continue
            for j in range(k):
                if cnt[j] < targets[j]:
                    cost = Dm[i][j] - Dm[i][a[i]]
                    if best is None or cost < best[0]: best = (cost, i, j)
        _, i, j = best; cnt[a[i]] -= 1; cnt[j] += 1; a[i] = j
    return [[sinks[i] for i in range(n) if a[i] == j] for j in range(k)]


def plan_r6(geo, islands, nb, leaf_n=4, side_hub=True, smax=150.0, tol_um=2.2, keepout=(), cap_w=None, ring_islands=False):
    """R6: entry -> [W/E branch -> side hub ->] 2 islands per side (master-plan sites, fixed) -> nb[i] B -> leaf_n leaves.
    Buffer at every branch point (k co-located branch buffers, one point-to-point wire each).  Per level all
    edges get the same length T_l: if the level spread exceeds tol_um, every edge is split into K_l>=2
    segments by repeaters on exact shortest-path waypoints (so GRT cannot shortcut the pad)."""
    core, entry, sinks, macros = read_geo(geo)
    mz = Maze(core, macros, keepout=keepout); ent = mz.cell(entry, node=False)
    isl = [mz.cell(p) for p in islands]; nleaf = sum(nb) * leaf_n; n = len(sinks)
    isl_moved = None
    if ring_islands:
        # PROPOSAL to the master plan: every island at the SAME maze distance from the entry (no level-1 pad)
        Tr = min(mz.md(ent, c_) for c_ in isl); new_ = []
        for c_ in isl: new_.append(on_ring(mz, ent, Tr, c_, tol=0)[0])
        isl_moved = [[mz.xy(o), mz.xy(q), round(mz.md(o, q), 2)] for o, q in zip(isl, new_)]; isl = new_
    tgt = [n * nb[i] * leaf_n // nleaf for i in range(4)]
    for i in range(n - sum(tgt)): tgt[i] += 1
    Q = assign(mz, sinks, isl, tgt)
    if cap_w is not None:
        sc = {s_: mz.cell(s_[:2], node=False) for s_ in sinks}; Wt = {s_: cap_w[s_] for s_ in sinks}
        tot = sum(Wt.values()); Dm = {s_: [mz.md(isl[j], sc[s_]) for j in range(4)] for s_ in sinks}
        tw = [tot * nb[j] * leaf_n / nleaf for j in range(4)]; w = [0.0] * 4; best = None
        for it in range(500):
            a = {s_: min(range(4), key=lambda j: Dm[s_][j] + w[j]) for s_ in sinks}; load = [0.0] * 4
            for s_, j in a.items(): load[j] += Wt[s_]
            err = max(abs(load[j] - tw[j]) / tw[j] for j in range(4))
            if best is None or err < best[0]: best = (err, dict(a))
            if err < 0.01: break
            for j in range(4): w[j] += 0.5 * (load[j] - tw[j]) / tw[j] * 20 / (1 + it / 50)
        Q = [[s_ for s_ in sinks if best[1][s_] == j] for j in range(4)]
    W = sorted(k for k in range(4) if mz.xy(isl[k])[0] < entry[0]); E = sorted(k for k in range(4) if k not in W)
    assert len(W) == 2 and len(E) == 2, 'need 2 islands per side'
    groups = {(): sinks}; site = {(): ent}
    if side_hub:
        top = [(0, 0, W[0]), (0, 1, W[1]), (1, 0, E[0]), (1, 1, E[1])]
        groups[(0,)] = Q[W[0]] + Q[W[1]]; groups[(1,)] = Q[E[0]] + Q[E[1]]
    else:
        top = [(0, W[0]), (1, W[1]), (2, E[0]), (3, E[1])]
    for t in top:
        g = t[:-1]; k = t[-1]; groups[g] = Q[k]; site[g] = isl[k]
        nbk = nb[k]
        bgs = split(Q[k], nbk) if cap_w is None else split_w(Q[k], nbk, cap_w)
        for bi, bg in enumerate(bgs):
            groups[g + (bi,)] = bg
            for li, lg in enumerate(split(bg, leaf_n) if cap_w is None else split_w(bg, leaf_n, cap_w)): groups[g + (bi, li)] = lg
    depth = max(len(g) for g in groups)
    for g in [x for x in groups if len(x) == depth]:
        pts = groups[g]; site[g] = mz.cell((sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)))
    for g in [x for x in groups if len(x) == depth - 1]:
        ch = [site[g + (i,)] for i in range(leaf_n)]
        site[g] = minimax_site(mz, ch, (round(sum(c[0] for c in ch) / leaf_n), round(sum(c[1] for c in ch) / leaf_n)))
    if side_hub:
        De = mz.bfs(ent)
        for s_ in (0, 1):
            D0 = mz.bfs(site[(s_, 0)]); D1 = mz.bfs(site[(s_, 1)]); b = None
            for i in range(mz.NX + 1):
                for j in range(mz.NY + 1):
                    if not mz.site_ok(i, j) or De[i][j] < 0 or D0[i][j] < 0 or D1[i][j] < 0: continue
                    if (mz.xy((i, j))[0] < entry[0]) != (s_ == 0): continue
                    v = (De[i][j] + max(D0[i][j], D1[i][j]), abs(D0[i][j] - D1[i][j]), -De[i][j])
                    if b is None or v < b[0]: b = (v, (i, j))
            site[(s_,)] = b[1]
    def nm(g): return 'R' if not g else 'T' + ''.join(str(i) for i in g)
    nodes = [('root', None, ent, BIG, 'entry')]; wires = []; last = {(): 'root'}; land = {}; T = []; K = []; spread = {}
    for lv in range(depth):
        gl = sorted(x for x in groups if len(x) == lv + 1)
        offs = {}
        for g in gl:
            par = g[:-1]; pc = site[par]; nsib = len([x for x in gl if x[:-1] == par])
            i_ = g[-1]; nrow = math.ceil(nsib / 2); col = i_ % 2 if nsib > 1 else 0.5; row = i_ // 2 if nsib > 1 else 0
            offs[g] = mz.cell((mz.xy(pc)[0] + (col - 0.5) * 1.08, mz.xy(pc)[1] + (row - (nrow - 1) / 2) * 1.08))
        L = {g: mz.md(offs[g], site[g]) for g in gl}; t = max(L.values()); sp = t - min(L.values())
        k = max(1, math.ceil(t / smax)); k = max(k, 2) if sp > tol_um else k
        T.append(t); K.append(k); spread[lv + 1] = round(sp, 2)
        for g in gl:
            bname = nm(g) + '_br'; nodes.append((bname, last[g[:-1]], offs[g], BIG, 'branch'))
            pts = exact_points(mz, offs[g], site[g], t if k > 1 else L[g], k); prev = bname; chain = [offs[g]] + pts + [site[g]]
            for i, c in enumerate(pts):
                nn = nm(g) + '_r%d' % i; nodes.append((nn, prev, c, REP, 'rep')); prev = nn
            segs = [mz.md(chain[i], chain[i + 1]) for i in range(len(chain) - 1)]
            wires.append(dict(level=lv + 1, edge=nm(g), segs=segs, cells=[mz.path(chain[i], chain[i + 1]) for i in range(len(chain) - 1)]))
            if lv == depth - 1: nodes.append((nm(g), prev, site[g], BIG, 'leaf'))
            else: land[prev] = (segs[-1], nm(g))
            last[g] = prev
    leaves = sorted(x for x in groups if len(x) == depth)
    leafsinks = {nm(g): groups[g] for g in leaves}
    mac = []
    for name, rect, ck in macros:
        c = mz.cell((ck[0] + 2.2, ck[1])); lf = min(leaves, key=lambda g: mz.md(site[g], c))
        mac.append((name, nm(lf), mz.cell((mz.xy(site[lf])[0] + 1.08, mz.xy(site[lf])[1]))))
    lvl = collections.defaultdict(list)
    for w_ in wires: lvl[w_['level']].append(round(sum(w_['segs']), 2))
    isl_groups = [g for g in groups if len(g) == (2 if side_hub else 1)]
    return dict(mz=mz, entry=entry, ent=ent, groups=groups, leaves=leaves, site=site, T=T, K=K, nodes=nodes, wires=wires, land=land,
                leafsinks=leafsinks, macros=mac, splits=['2x2' if side_hub else 4, nb, leaf_n], nm=nm, isl_groups=isl_groups,
                level_range_um={l: [min(v), max(v)] for l, v in lvl.items()}, level_spread_um=spread, islands_moved=isl_moved)



# ---------------------------------------------------------------- equal-capacitance grouping (plan geometry only)
def sink_weights(sinks, c_ff_um, cpin=0.5, k=2):
    """per-sink load estimate = pin C + wire C of half the distance to its k nearest neighbours (MST share)."""
    B = collections.defaultdict(list)
    for i, s in enumerate(sinks): B[(int(s[0] // 10), int(s[1] // 10))].append(i)
    w = {}
    for i, s in enumerate(sinks):
        bx, by = int(s[0] // 10), int(s[1] // 10); r = 1; ds = []
        while True:
            ds = sorted(abs(sinks[j][0] - s[0]) + abs(sinks[j][1] - s[1]) for x in range(bx - r, bx + r + 1) for y in range(by - r, by + r + 1)
                        for j in B.get((x, y), ()) if j != i)
            if len(ds) >= k and ds[k - 1] <= 10 * r: break
            r += 1
            if r > 30: break
        w[s] = cpin + c_ff_um * sum(ds[:k]) / max(1, len(ds[:k]))
    return w


def balanced_w(points, k, centre_dist, weight, iters=500):
    """equal-WEIGHT power-diagram split (weights = estimated C)."""
    n = len(points); tot = sum(weight[p] for p in points); tgt = tot / k
    Dm = [[centre_dist(p, c) for c in range(k)] for p in points]; w = [0.0] * k
    best = None
    for it in range(iters):
        a = [min(range(k), key=lambda c: Dm[i][c] + w[c]) for i in range(n)]
        load = [0.0] * k
        for i in range(n): load[a[i]] += weight[points[i]]
        err = max(abs(l - tgt) for l in load)
        if best is None or err < best[0]: best = (err, list(a))
        if err < 0.01 * tgt: break
        for c in range(k): w[c] += 0.5 * (load[c] - tgt) / tgt * 20 / (1 + it / 50)
    a = best[1]
    return [[points[i] for i in range(n) if a[i] == c] for c in range(k)]


def split_w(pts, k, weight):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    ax = 0 if max(xs) - min(xs) > max(ys) - min(ys) else 1
    srt = sorted(pts, key=lambda p: p[ax]); cs = [srt[int((i + .5) * len(srt) / k)][:2] for i in range(k)]
    for _ in range(6):
        grp = balanced_w(pts, k, lambda s, c: abs(s[0] - cs[c][0]) + abs(s[1] - cs[c][1]), weight, iters=300)
        grp = [g for g in grp if g] or grp
        cs = [(sorted(p[0] for p in g)[len(g) // 2], sorted(p[1] for p in g)[len(g) // 2]) for g in grp]
    return grp


if __name__ == '__main__':
    main()
