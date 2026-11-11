#!/usr/bin/env python3
"""CPL-QC-2 (lane cpl-qc-2, 11-11) clean-slate intra-type placement evaluator for QC types.  ADVISORY, DO_NOT_COUNT.

Model: the bound kit RTL (svgraph.py JSON) gives every >=16-bit connection between hard-core pin groups, top ports
(face windows) and soft instances (stations, fabric, straps).  Hard pins sit at their pin-group centroid for the given
origin/orient; ports at their face-window centre; plan-placed station/ft registers at their plan sites; every other soft
instance at the bit-weighted mean of its neighbours (iterated), snapped to the nearest street cell.  Each link is routed on
a 17.28-um grid by a negotiated-congestion shortest path (3 passes).  Capacity per cell (tracks): street = all of M2-M7 in
the routing direction x (1 - flow derate) (route_supply constants); over a hard core = only what is above its OBS:
  NK/NL A0 tiles: OBS M1-M7 with the signed detail view (M6/M7 internal wires) -> M6/M7 free fraction from the detail LEF;
  SRAM/ROM (obs_max M4): H = M6, V = M5/2 (OpenROAD halving) + M7;  other hard cores (obs M5): H = M6/2, V = M7.
Outputs: bit-mm (routed), overflow (bits over capacity, summed over cells), worst line cut (demand/supply), p99 cell use.

  cslate.py eval   PLAN TYPE GRAPH [--delta D.json] [--out O.json]
  cslate.py search PLAN TYPE GRAPH --out O.json         (2x2 A0 tile families: slot permutation x orient)
"""
import argparse, copy, heapq, itertools, json, math, os, re, sys
import numpy as np

PITCH = {'M2': 0.0419, 'M3': 0.0371, 'M4': 0.048, 'M5': 0.0503, 'M6': 0.074, 'M7': 0.0681}
DER = {'M2': .2914, 'M3': .2573, 'M4': .2568, 'M5': .2599, 'M6': .3118, 'M7': .3239}
T = {L: (1 - DER[L]) / PITCH[L] for L in PITCH}
STREET_DERATE = 0.6   # streets also carry the dense glue/repair-buffer local wiring (measured 200-350 cells/100 um2 on cl622 a20)
H_STREET = (T['M2'] + T['M4'] + T['M6']) * STREET_DERATE
V_STREET = (T['M3'] + T['M5'] + T['M7']) * STREET_DERATE
G = 17.28
REACH = 405.0
LAT = 4.32
MIN_GAP = 34.56
EDGE = 4.32
ORIENTS = ('R0', 'MY', 'MX', 'R180')
DETAIL = {}          # module -> (free6, free7) arrays in tile-local cells of size G


def load(p):
    with open(p) as f:
        return json.load(f)


def xform(origin, size, orient, x, y):
    w, h = size
    if orient in ('MY', 'R180'):
        x = w - x
    if orient in ('MX', 'R180'):
        y = h - y
    return origin[0] + x, origin[1] + y


def detail_free(lef, size):
    """free-track fraction of M6 (H) and M7 (V) per G cell in the core frame, from a detail view LEF (OBS rects)."""
    w, h = size
    nx, ny = int(math.ceil(w / G)), int(math.ceil(h / G))
    occ = {'M6': np.zeros((nx, ny)), 'M7': np.zeros((nx, ny))}
    pitch = {'M6': 0.064, 'M7': 0.064}
    lay = None
    inobs = False
    with open(lef) as f:
        for line in f:
            s = line.split()
            if not s:
                continue
            if s[0] == 'OBS':
                inobs = True; continue
            if not inobs:
                continue
            if s[0] == 'LAYER':
                lay = s[1]; continue
            if s[0] == 'RECT' and lay in occ:
                x0, y0, x1, y1 = map(float, s[1:5])
                if (x1 - x0) * (y1 - y0) > 1000:      # full-cover rect (base OBS) -> ignore, detail replaces it
                    continue
                # blocked tracks: an H wire on M6 blocks ceil(height/pitch) tracks over its length
                if lay == 'M6':
                    trk = max(1, math.ceil((y1 - y0) / pitch['M6'] - 1e-6)); span = (x0, x1); cy = (y0 + y1) / 2
                    i0, i1 = int(x0 // G), int(min(x1, w - 1e-6) // G); j = int(min(cy, h - 1e-6) // G)
                    for i in range(i0, i1 + 1):
                        a = max(x0, i * G); b = min(x1, (i + 1) * G)
                        if b > a:
                            occ['M6'][i, j] += trk * (b - a) / G
                else:
                    trk = max(1, math.ceil((x1 - x0) / pitch['M7'] - 1e-6)); cx = (x0 + x1) / 2
                    j0, j1 = int(y0 // G), int(min(y1, h - 1e-6) // G); i = int(min(cx, w - 1e-6) // G)
                    for j in range(j0, j1 + 1):
                        a = max(y0, j * G); b = min(y1, (j + 1) * G)
                        if b > a:
                            occ['M7'][i, j] += trk * (b - a) / G
    cap6 = G / pitch['M6']; cap7 = G / pitch['M7']
    return np.clip(1 - occ['M6'] / cap6, 0, 1), np.clip(1 - occ['M7'] / cap7, 0, 1)


class Type:
    def __init__(self, plan_path, tname, graph_path, detail=None):
        self.plan = load(plan_path)
        self.pdir = os.path.dirname(os.path.abspath(plan_path))
        self.name = tname
        self.t = self.plan['partition_types'][tname]
        self.W, self.H = self.t['outline_um']
        self.cores = {c['inst']: c for c in self.t['hard_cores']}
        self.g = load(graph_path)
        self._pins = {}
        self.detail = detail or {}
        # rtl name -> plan inst
        self.rmap = {}
        rtl = set(self.g['insts'])
        for i, c in self.cores.items():
            cands = [i, 'u_' + i, (c.get('physical_inst') or '').split('.')[-1]]
            if i.startswith('cl_'):
                cands.append('u_cland_' + i[3:])
            m = re.match(r'u_t(\d)(\d)$', i)
            if m:
                cands.append('u_u_t_%s_%s' % m.groups())
            for k in cands:
                if k in rtl:
                    self.rmap[k] = i
                    break
        self.groups = {i: self._groups(c) for i, c in self.cores.items()}
        self.ports = self._ports()
        self.fixed_soft = self._fixed_soft()
        self.links = self._links()

    def pins(self, c):
        pf = c.get('pins_file')
        if pf not in self._pins:
            self._pins[pf] = load(os.path.join(self.pdir, pf))['pins'] if pf else []
        return self._pins[pf]

    def _groups(self, c):
        g = {}
        for p in self.pins(c):
            b = p['name'].split('[')[0]
            e = g.setdefault(b, [0, 0.0, 0.0, 1e9, 1e9, -1e9, -1e9])
            e[0] += 1; e[1] += p['x']; e[2] += p['y']
            e[3] = min(e[3], p['x']); e[4] = min(e[4], p['y']); e[5] = max(e[5], p['x']); e[6] = max(e[6], p['y'])
        self.gext = getattr(self, 'gext', {})
        return {b: (e[1] / e[0], e[2] / e[0], e[0], e[3], e[4], e[5], e[6]) for b, e in g.items()}

    def _ports(self):
        out = {}
        W, H = self.W, self.H
        for b in self.t['buses']:
            m = (b['window_um'][0] + b['window_um'][1]) / 2
            out[b['name']] = {'N': (m, H), 'S': (m, 0.0), 'E': (W, m), 'W': (0.0, m)}[b['face']]
        for f in self.t.get('ft_slots', []):
            ow = f.get('out_window_um'); iw = f.get('in_window_um')
            if ow:
                m = (ow[0] + ow[1]) / 2
                out[f['name'] + '_o'] = {'N': (m, H), 'S': (m, 0.0), 'E': (W, m), 'W': (0.0, m)}[f['out_face']]
            if iw:
                m = (iw[0] + iw[1]) / 2
                out[f['name'] + '_i'] = {'N': (m, H), 'S': (m, 0.0), 'E': (W, m), 'W': (0.0, m)}[f['in_face']]
        return out

    def _fixed_soft(self):
        fx = {}
        for s in self.t.get('internal_stations', []):
            conn = s['conn'].split(':', 1)[-1]
            for k, r in enumerate(s.get('regs_um', [])):
                fx['u_ist_%s_%d' % (conn, k)] = tuple(r)
        for f in self.t.get('ft_slots', []):
            for k, r in enumerate(f.get('regs_um', [])):
                fx['u_ft_%s_o_%d' % (f['name'], k)] = tuple(r)
        return fx

    def _links(self):
        # multi-stage pads (u_lpad_<conn>, one RTL instance = the plan's N FIRM station regs) are expanded into a chain
        nst = {s['conn'].split(':', 1)[-1]: len(s.get('regs_um', [])) for s in self.t.get('internal_stations', [])}
        self.chains = {}
        L = []

        def rew(obj):
            inst, _, port = obj.partition('.')
            if inst.startswith('u_lpad_') and inst[7:] in nst and nst[inst[7:]]:
                c = inst[7:]; n = nst[c]
                return 'u_ist_%s_%d' % (c, 0 if port == 'd' else n - 1)
            return obj
        for a, b, w in self.g['edges']:
            if w < 16:
                continue
            a2, b2 = rew(a), rew(b)
            L.append((self._node(a2), self._node(b2), w, a + ' -- ' + b))
        for c, n in nst.items():
            if 'u_lpad_' + c in self.g['insts']:
                w = next(s['bits'] for s in self.t['internal_stations'] if s['conn'].split(':', 1)[-1] == c)
                for k in range(n - 1):
                    L.append((('S', 'u_ist_%s_%d' % (c, k)), ('S', 'u_ist_%s_%d' % (c, k + 1)), w, 'lpad %s %d' % (c, k)))
        for c, n in nst.items():
            self.chains[c] = ['u_ist_%s_%d' % (c, k) for k in range(n)]
        # hard cores buried inside a soft top-level block (SRAM/ROM macros of coll/tt/glue types): tie each to its block
        mapped = set(self.rmap.values())
        self.parent = {}
        for i, c in self.cores.items():
            if i in mapped:
                continue
            path = (c.get('physical_inst') or i)
            if path.startswith('u_bound.'):
                path = path[len('u_bound.'):]
            top = path.split('.')[0]
            for k in (top, 'u_' + top, top.replace('[', '_').replace(']', '')):
                if k in self.g['insts']:
                    npin = sum(g[2] for g in self.groups[i].values())
                    L.append((('H', i, '*'), ('S', k), max(16, min(512, npin // 2)), 'macro %s in %s' % (i, k)))
                    self.parent[i] = k
                    break
        return L

    def _node(self, obj):
        if obj.startswith('PORT:'):
            p = obj[5:]
            if p in self.ports:
                return ('P', p)
            return ('S', obj)            # unplaced port (no window): treat as soft
        inst, _, port = obj.partition('.')
        if inst in self.rmap:
            return ('H', self.rmap[inst], port)
        return ('S', inst)

    # ---------------------------------------------------------------- placement state
    def place(self, delta=None):
        """returns dict inst -> (origin, orient) after applying delta {inst: [x, y, orient]}"""
        st = {i: (tuple(c['origin_um']), c.get('orient', 'R0')) for i, c in self.cores.items()}
        for i, v in (delta or {}).items():
            st[i] = ((v[0], v[1]), v[2])
        return st

    def rects(self, st):
        return {i: (o[0], o[1], o[0] + self.cores[i]['outline_um'][0], o[1] + self.cores[i]['outline_um'][1])
                for i, (o, _) in st.items()}

    def hpos(self, st, inst, port):
        c = self.cores[inst]
        g = self.groups[inst].get(port)
        if g is None:
            ox, oy = st[inst][0]; w, h = c['outline_um']
            return (ox + w / 2, oy + h / 2)
        return xform(st[inst][0], c['outline_um'], st[inst][1], g[0], g[1])

    def positions(self, st, soft_fixed=None, iters=60):
        sf = dict(self.fixed_soft)
        sf.update(soft_fixed or {})
        pos = {}
        soft = set()
        for p, q, w, _ in self.links:
            for n in (p, q):
                if n[0] == 'S':
                    soft.add(n[1])
        nb = {s: [] for s in soft}
        for p, q, w, _ in self.links:
            if p[0] == 'S':
                nb[p[1]].append((q, w))
            if q[0] == 'S':
                nb[q[1]].append((p, w))

        def fixedpos(n):
            if n[0] == 'H':
                return self.hpos(st, n[1], n[2])
            if n[0] == 'P':
                return self.ports[n[1]]
            return None
        cur = {}
        for s in soft:
            if s in sf:
                cur[s] = sf[s]
            else:
                cur[s] = (self.W / 2, self.H / 2)
        for _ in range(iters):
            new = {}
            for s in soft:
                if s in sf:
                    new[s] = sf[s]; continue
                sx = sy = sw = 0.0
                for n, w in nb[s]:
                    p = fixedpos(n) if n[0] != 'S' else cur[n[1]]
                    sx += w * p[0]; sy += w * p[1]; sw += w
                new[s] = (sx / sw, sy / sw) if sw else cur[s]
            cur = new
        rs = list(self.rects(st).values())
        for s in soft:
            if s in sf:
                continue
            cur[s] = snap_free(cur[s], rs, self.W, self.H)
        return cur

    # ---------------------------------------------------------------- capacity grid
    def grid(self, st):
        nx, ny = int(math.ceil(self.W / G)), int(math.ceil(self.H / G))
        capH = np.full((nx, ny), H_STREET * G)
        capV = np.full((nx, ny), V_STREET * G)
        mac = np.zeros((nx, ny), dtype=bool)
        for i, (o, ori) in st.items():
            c = self.cores[i]
            w, h = c['outline_um']
            x0, y0 = o
            mod = c['module']
            obs = c.get('obs_max', 'M5')
            if mod in self.detail:
                f6, f7 = self.detail[mod]
            else:
                f6 = f7 = None
            for a in range(int(x0 // G), int(min(x0 + w, self.W - 1e-6) // G) + 1):
                for b in range(int(y0 // G), int(min(y0 + h, self.H - 1e-6) // G) + 1):
                    cx0, cy0 = a * G, b * G
                    ov = max(0, min(cx0 + G, x0 + w) - max(cx0, x0)) * max(0, min(cy0 + G, y0 + h) - max(cy0, y0)) / (G * G)
                    if ov <= 0:
                        continue
                    if f6 is not None:
                        lx, ly = (cx0 + G / 2 - x0), (cy0 + G / 2 - y0)
                        if ori in ('MY', 'R180'):
                            lx = w - lx
                        if ori in ('MX', 'R180'):
                            ly = h - ly
                        li = min(max(int(lx // G), 0), f6.shape[0] - 1); lj = min(max(int(ly // G), 0), f6.shape[1] - 1)
                        # stock GRT: M6 over the tile behaves as the halved transition layer (cbx_q10 a25: 8858 ov stock,
                        # 0 with halving off, GRT-PATCH-1); the detail view's own M6/M7 wires come off on top
                        mh = T['M6'] / 2 * G * f6[li, lj]; mv = T['M7'] * G * f7[li, lj]
                    elif obs == 'M4':
                        mh = T['M6'] * G; mv = (T['M5'] / 2 + T['M7']) * G
                    else:
                        mh = T['M6'] / 2 * G; mv = T['M7'] * G
                    capH[a, b] = capH[a, b] * (1 - ov) + mh * ov
                    capV[a, b] = capV[a, b] * (1 - ov) + mv * ov
                    if ov > 0.5:
                        mac[a, b] = True
        return capH, capV, mac

    # ---------------------------------------------------------------- routing + metrics
    def evaluate(self, st, soft_fixed=None, passes=3, keep_paths=False):
        pos = self.positions(st, soft_fixed)
        capH, capV, mac = self.grid(st)
        nx, ny = capH.shape

        def cell(p):
            return (min(max(int(p[0] // G), 0), nx - 1), min(max(int(p[1] // G), 0), ny - 1))

        def P(n):
            if n[0] == 'H':
                return self.hpos(st, n[1], n[2])
            if n[0] == 'P':
                return self.ports[n[1]]
            return pos[n[1]]
        def ext(n):
            # endpoints spread along the pin group / window / soft cloud extent
            if n[0] == 'H':
                c = self.cores[n[1]]; g = self.groups[n[1]].get(n[2])
                if g:
                    a = xform(st[n[1]][0], c['outline_um'], st[n[1]][1], g[3], g[4])
                    b = xform(st[n[1]][0], c['outline_um'], st[n[1]][1], g[5], g[6])
                    return a, b
            if n[0] == 'P':
                for bb in self.t['buses']:
                    if bb['name'] == n[1]:
                        w0, w1 = bb['window_um']; f = bb['face']
                        return ({'N': (w0, self.H), 'S': (w0, 0.0), 'E': (self.W, w0), 'W': (0.0, w0)}[f],
                                {'N': (w1, self.H), 'S': (w1, 0.0), 'E': (self.W, w1), 'W': (0.0, w1)}[f])
            p = P(n)
            return p, p
        nets = []
        for p, q, w, lab in self.links:
            k = max(1, int(math.ceil(w / 128)))
            (a0, a1), (b0, b1) = ext(p), ext(q)
            for j in range(k):
                f = (j + 0.5) / k
                pa = (a0[0] + f * (a1[0] - a0[0]), a0[1] + f * (a1[1] - a0[1]))
                pb = (b0[0] + f * (b1[0] - b0[0]), b0[1] + f * (b1[1] - b0[1]))
                nets.append((cell(pa), cell(pb), w / k, lab, pa, pb))
        nets.sort(key=lambda r: -r[2])
        useH = np.zeros((nx, ny)); useV = np.zeros((nx, ny))
        histH = np.zeros((nx, ny)); histV = np.zeros((nx, ny))
        paths = [None] * len(nets)
        for it in range(passes):
            for k, (a, b, w, lab, pa, pb) in enumerate(nets):
                if paths[k] is not None:
                    apply(paths[k], w, useH, useV, -1)
                pres = 0.5 * (2 ** it)
                paths[k] = route(a, b, w, useH, useV, capH, capV, histH, histV, pres)
                apply(paths[k], w, useH, useV, +1)
            oH = np.maximum(useH - capH, 0); oV = np.maximum(useV - capV, 0)
            histH += (oH > 0) * 1.0; histV += (oV > 0) * 1.0
        bitmm = 0.0
        hop = []
        for k, (a, b, w, lab, pa, pb) in enumerate(nets):
            L = max(len(paths[k]) - 1, 0) * G
            bitmm += w * L / 1000
            hop.append((round(L, 1), lab))
        oH = np.maximum(useH - capH, 0); oV = np.maximum(useV - capV, 0)
        uH = useH / np.maximum(capH, 1e-3); uV = useV / np.maximum(capV, 1e-3)
        used = np.concatenate([uH[useH > 0], uV[useV > 0]])
        # line cuts: horizontal line between rows j and j+1 -> V demand / V supply across the row
        cutsH = [(round((j + 1) * G, 1), useV[:, j].sum(), capV[:, j].sum()) for j in range(ny)]
        cutsV = [(round((i + 1) * G, 1), useH[i, :].sum(), capH[i, :].sum()) for i in range(nx)]
        wH = max(cutsH, key=lambda r: r[1] / r[2]); wV = max(cutsV, key=lambda r: r[1] / r[2])
        res = {'bitmm': round(bitmm, 1), 'overflow': int(oH.sum() + oV.sum()), 'overflow_H': int(oH.sum()),
               'overflow_V': int(oV.sum()),
               'overflow_over_macro': int((oH * mac).sum() + (oV * mac).sum()),
               'p99_use': round(float(np.percentile(used, 99)), 3) if used.size else 0.0,
               'max_use_street': round(float(max((uH * ~mac).max(), (uV * ~mac).max())), 3),
               'max_use_macro': round(float(max((uH * mac).max(), (uV * mac).max())), 3),
               'worst_cut_Hline': {'y': wH[0], 'bits': int(wH[1]), 'supply': int(wH[2]), 'ratio': round(wH[1] / wH[2], 3)},
               'worst_cut_Vline': {'x': wV[0], 'bits': int(wV[1]), 'supply': int(wV[2]), 'ratio': round(wV[1] / wV[2], 3)},
               'longest_links': sorted(hop, reverse=True)[:8], 'n_links': len(nets)}
        if keep_paths:
            res['_paths'] = [(nets[k][2], nets[k][3], [(c[0] * G + G / 2, c[1] * G + G / 2) for c in paths[k]])
                             for k in range(len(nets))]
            res['_pos'] = pos
            res['_useH'] = (useH / np.maximum(capH, 1e-3)).tolist()
            res['_useV'] = (useV / np.maximum(capV, 1e-3)).tolist()
        return res


def snap_free(p, rs, W, H):
    x, y = p
    for r in rs:
        if r[0] < x < r[2] and r[1] < y < r[3]:
            d = [(x - r[0] + 2, (r[0] - 2, y)), (r[2] - x + 2, (r[2] + 2, y)), (y - r[1] + 2, (x, r[1] - 2)),
                 (r[3] - y + 2, (x, r[3] + 2))]
            d.sort()
            for _, q in d:
                if 0 < q[0] < W and 0 < q[1] < H and not any(s[0] < q[0] < s[2] and s[1] < q[1] < s[3] for s in rs):
                    return q
            return d[0][1]
    return (x, y)


def apply(path, w, useH, useV, sgn):
    for (a, b), (c, d) in zip(path, path[1:]):
        if a != c:   # horizontal step: H usage on both cells' half -> charge the cell we leave and enter
            useH[a, b] += sgn * w * 0.5; useH[c, d] += sgn * w * 0.5
        else:
            useV[a, b] += sgn * w * 0.5; useV[c, d] += sgn * w * 0.5


def route(a, b, w, useH, useV, capH, capV, histH, histV, pres):
    nx, ny = useH.shape
    if a == b:
        return [a]
    INF = float('inf')
    dist = {a: 0.0}
    prev = {}
    pq = [(abs(a[0] - b[0]) + abs(a[1] - b[1]), 0.0, a)]
    while pq:
        f, d, u = heapq.heappop(pq)
        if u == b:
            break
        if d > dist.get(u, INF):
            continue
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            v = (u[0] + dx, u[1] + dy)
            if not (0 <= v[0] < nx and 0 <= v[1] < ny):
                continue
            if dx:
                cap = capH[v]; use = useH[v]; hist = histH[v]
            else:
                cap = capV[v]; use = useV[v]; hist = histV[v]
            over = (use + w) / max(cap, 1e-3)
            c = 1.0 + hist * 0.3 + (pres * (over - 0.9) * 4 if over > 0.9 else 0.0) + (20.0 if cap < w * 0.2 else 0.0)
            nd = d + c
            if nd < dist.get(v, INF):
                dist[v] = nd; prev[v] = u
                heapq.heappush(pq, (nd + abs(v[0] - b[0]) + abs(v[1] - b[1]), nd, v))
    path = [b]
    while path[-1] != a:
        path.append(prev[path[-1]])
    return path[::-1]


def legal(ty, st, extra_pts=()):
    """B34-style legality: lattice, outline edge, min gap between big cores, bands/ft/station/clock-tap not inside cores."""
    errs = []
    rs = ty.rects(st)
    for i, r in rs.items():
        o = st[i][0]
        if r[0] < EDGE - 1e-6 or r[1] < EDGE - 1e-6 or r[2] > ty.W - EDGE + 1e-6 or r[3] > ty.H - EDGE + 1e-6:
            errs.append(f'{i} outside outline-{EDGE}')
        if abs(o[0] / LAT - round(o[0] / LAT)) > 1e-6 or abs(o[1] / LAT - round(o[1] / LAT)) > 1e-6:
            errs.append(f'{i} off lattice {o}')
    for (i, a), (j, b) in itertools.combinations(rs.items(), 2):
        gx = max(b[0] - a[2], a[0] - b[2]); gy = max(b[1] - a[3], a[1] - b[3])
        big = ty.cores[i]['outline_um'][0] * ty.cores[i]['outline_um'][1] > 20000 and \
            ty.cores[j]['outline_um'][0] * ty.cores[j]['outline_um'][1] > 20000
        if gx < 0 and gy < 0:
            errs.append(f'overlap {i} {j}')
        elif big and max(gx, gy) < MIN_GAP - 1e-6:
            errs.append(f'gap {i} {j} {max(gx, gy):.2f} < {MIN_GAP}')
    bands = (ty.t.get('clock', {}).get('landing_contract') or {}).get('bands') or {}
    for bn, bd in (bands.items() if isinstance(bands, dict) else []):
        rr = bd.get('rect_um')
        if rr:
            for i, r in rs.items():
                if rr[0] < r[2] - 1e-6 and r[0] < rr[2] - 1e-6 and rr[1] < r[3] - 1e-6 and r[1] < rr[3] - 1e-6:
                    errs.append(f'band {bn} overlaps {i}')
    for nm, p in extra_pts:
        for i, r in rs.items():
            if r[0] + 0.5 < p[0] < r[2] - 0.5 and r[1] + 0.5 < p[1] < r[3] - 0.5:
                errs.append(f'{nm} {p} inside {i}')
    tap = ty.t.get('clock', {}).get('tap_um')
    if tap:
        for i, r in rs.items():
            if r[0] < tap[0] < r[2] and r[1] < tap[1] < r[3]:
                errs.append(f'clock tap_um {tap} inside {i}')
    return errs


def seg_in_rects(p, q, rs):
    """length of the axis-parallel segment p-q inside any rect."""
    L = 0.0
    for r in rs:
        if p[1] == q[1]:
            if r[1] < p[1] < r[3]:
                a, b = sorted((p[0], q[0]))
                L += max(0.0, min(b, r[2]) - max(a, r[0]))
        else:
            if r[0] < p[0] < r[2]:
                a, b = sorted((p[1], q[1]))
                L += max(0.0, min(b, r[3]) - max(a, r[1]))
    return L


def proxy(ty, st, free_ist=True, pen=12.0):
    """fast screen: bit-weighted Manhattan + penalty x length an L route must spend over a big core (best of 2 L's)."""
    sf = {k: v for k, v in ty.fixed_soft.items() if not (free_ist and k.startswith('u_ist_'))}
    save = ty.fixed_soft
    ty.fixed_soft = sf
    pos = ty.positions(st, iters=40)
    ty.fixed_soft = save
    rs = [r for i, r in ty.rects(st).items() if ty.cores[i]['outline_um'][0] * ty.cores[i]['outline_um'][1] > 20000]

    def P(n):
        if n[0] == 'H':
            return ty.hpos(st, n[1], n[2])
        if n[0] == 'P':
            return ty.ports[n[1]]
        return pos[n[1]]
    tot = 0.0
    over = 0.0
    for p, q, w, _ in ty.links:
        a, b = P(p), P(q)
        man = abs(a[0] - b[0]) + abs(a[1] - b[1])
        c1 = (b[0], a[1]); c2 = (a[0], b[1])
        o1 = seg_in_rects(a, c1, rs) + seg_in_rects(c1, b, rs)
        o2 = seg_in_rects(a, c2, rs) + seg_in_rects(c2, b, rs)
        o = min(o1, o2)
        tot += w * man / 1000; over += w * o / 1000
    return tot + pen * over, tot, over, pos


def restation(ty, st):
    """re-place every FIRM internal-station register (same count) at equal arc-length fractions of the street-first
    shortest path between the chain's two neighbours (face window / core pin / soft endpoint).  Returns
    ({reg_inst: (x, y)}, {conn: {'from', 'to', 'regs', 'path_um', 'hop_um'}})."""
    sf = {k: v for k, v in ty.fixed_soft.items() if not k.startswith('u_ist_')}
    save = ty.fixed_soft; ty.fixed_soft = sf
    pos = ty.positions(st, iters=60)
    ty.fixed_soft = save
    capH, capV, mac = ty.grid(st)
    nx, ny = capH.shape
    zero = np.zeros_like(capH)
    nb = {}
    for p, q, w, _ in ty.links:
        for x, y in ((p, q), (q, p)):
            if x[0] == 'S':
                nb.setdefault(x[1], []).append(y)

    def P(n):
        if n[0] == 'H':
            return ty.hpos(st, n[1], n[2])
        if n[0] == 'P':
            return ty.ports[n[1]]
        return pos[n[1]]
    out, info = {}, {}
    for c, regs in ty.chains.items():
        if not regs:
            continue
        ends = []
        for k, r in ((0, regs[0]), (len(regs) - 1, regs[-1])):
            if r not in nb:
                ends.append(None); continue
            others = [n for n in nb.get(r, []) if not (n[0] == 'S' and n[1] in regs)]
            if not others:
                ends.append(None); continue
            ends.append(P(others[0]))
        # plan semantics first: the station spans face point <-> core pin named by launch/capture
        sdef = next((s for s in ty.t.get('internal_stations', []) if s['conn'].split(':', 1)[-1] == c), None)
        if sdef:
            pin = None
            for key in ('capture', 'launch'):
                v = sdef.get(key) or ''
                inst, _, prt = v.partition('.')
                if inst in ty.cores and prt:
                    pin = ty.hpos(st, inst, prt.split('[')[0]); break
            fa, ta = sdef['from_um'], sdef['to_um']
            onf = lambda p: p[0] < 0.6 or p[1] < 0.6 or p[0] > ty.W - 0.6 or p[1] > ty.H - 0.6
            if pin is not None:
                if onf(fa):
                    ends = [tuple(fa), pin]
                elif onf(ta):
                    ends = [pin, tuple(ta)]
        if None in ends:
            continue
        a, b = ends
        ca = (min(max(int(a[0] // G), 0), nx - 1), min(max(int(a[1] // G), 0), ny - 1))
        cb = (min(max(int(b[0] // G), 0), nx - 1), min(max(int(b[1] // G), 0), ny - 1))
        # street-first: macro cells cost 40x
        cH = np.where(mac, 0.0, capH) + 1e-3; cV = np.where(mac, 0.0, capV) + 1e-3
        path = route(ca, cb, 1.0, zero, zero, cH, cV, zero, zero, 0.0)
        pts = [a] + [(i * G + G / 2, j * G + G / 2) for i, j in path[1:-1]] + [b]
        seg = [abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(pts, pts[1:])]
        L = sum(seg)
        n = len(regs)
        rr = []
        for k in range(1, n + 1):
            d = L * k / (n + 1)
            for (p, q), l in zip(zip(pts, pts[1:]), seg):
                if d <= l + 1e-9:
                    f = d / l if l else 0
                    rr.append((round((p[0] + f * (q[0] - p[0])) / 0.27) * 0.27, round((p[1] + f * (q[1] - p[1])) / 0.27) * 0.27))
                    break
                d -= l
        rr = [(round(x, 3), round(y, 3)) for x, y in rr]
        for r, xy in zip(regs, rr):
            out[r] = xy
        info[c] = {'from': a, 'to': b, 'regs': rr, 'path_um': round(L, 1), 'hop_um': round(L / (n + 1), 1)}
    return out, info


def search_2x2(ty, top=12, orients=ORIENTS):
    big = [i for i, c in ty.cores.items() if c['outline_um'][0] * c['outline_um'][1] > 200000]
    slots = [tuple(ty.cores[i]['origin_um']) for i in big]
    st0 = ty.place()
    res = []
    for perm in itertools.permutations(big):
        if any(ty.cores[a]['outline_um'] != ty.cores[b]['outline_um'] for a, b in zip(perm, big)):
            continue
        for ors in itertools.product(orients, repeat=len(big)):
            st = dict(st0)
            for inst, slot, o in zip(perm, slots, ors):
                st[inst] = (slot, o)
            s, man, over, _ = proxy(ty, st)
            res.append((s, man, over, {i: [st[i][0][0], st[i][0][1], st[i][1]] for i in big}))
    res.sort(key=lambda r: r[0])
    return res[:top], len(res)


def geom_variants(ty, d):
    """street re-allocation for a 2x2 tile arrangement d: symmetric W/E margins m (centre channel = rest) and the
    middle gap g (top/bottom margins split the rest), all on the 4.32 lattice."""
    big = list(d)
    w, h = ty.cores[big[0]]['outline_um']
    xs = sorted({v[0] for v in d.values()}); ys = sorted({v[1] for v in d.values()})
    if len(xs) != 2 or len(ys) != 2:
        return []
    out = []
    for m in (43.2, 60.48, 77.76, 86.4, 95.04):
        xl = m; xr = round((ty.W - m - w) / LAT) * LAT
        if xr - (xl + w) < MIN_GAP:
            continue
        for gap in (69.12, 77.76, 86.4, 103.68, 120.96):
            rest = ty.H - 2 * h - gap
            yb = math.floor(rest / 2 / LAT) * LAT
            if yb < EDGE + 8.64:
                continue
            yt = round((yb + h + gap) / LAT) * LAT
            if yt + h > ty.H - EDGE:
                continue
            nd = {}
            for i, (x, y, o) in d.items():
                nd[i] = [round(xl if x == xs[0] else xr, 2), round(yb if y == ys[0] else yt, 2), o]
            out.append(((m, gap), nd))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd')
    ap.add_argument('plan'); ap.add_argument('type'); ap.add_argument('graph')
    ap.add_argument('--delta'); ap.add_argument('--out')
    ap.add_argument('--detail', action='append', default=[], help='MODULE=LEF')
    ap.add_argument('--paths', action='store_true')
    ap.add_argument('--top', type=int, default=12)
    ap.add_argument('--orients', default='R0,MY', help='allowed orients (MX/R180 put the NK/NL M4 face pins half a pitch off the parent M4 grid; no QC hard core uses them)')
    a = ap.parse_args()
    det = {}
    for d in a.detail:
        m, l = d.split('=', 1)
        det[m] = None
    ty0 = Type(a.plan, a.type, a.graph)
    for d in a.detail:
        m, l = d.split('=', 1)
        sz = next(c['outline_um'] for c in ty0.t['hard_cores'] if c['module'] == m) if any(
            c['module'] == m for c in ty0.t['hard_cores']) else None
        if sz:
            det[m] = detail_free(l, sz)
    det = {k: v for k, v in det.items() if v is not None}
    ty = Type(a.plan, a.type, a.graph, det)
    if a.cmd == 'search':
        base = ty.place()
        rb = ty.evaluate(base)
        top, n = search_2x2(ty, a.top, tuple(a.orients.split(',')))
        pts0 = [('ist ' + k, v) for k, v in ty.fixed_soft.items() if k.startswith('u_ist_')] + [('ft ' + k, v) for k, v in ty.fixed_soft.items() if k.startswith('u_ft_')]
        cands = []
        for s, man, over, d in top:
            st = ty.place(d)
            regs, info = restation(ty, st)
            r = ty.evaluate(st, soft_fixed=regs)
            pts = [('ist ' + k, v) for k, v in regs.items()] + [('ft ' + k, v) for k, v in ty.fixed_soft.items() if k.startswith('u_ft_')]
            errs = [e for e in legal(ty, st, pts) if e not in legal(ty, base, pts0)]
            maxhop = max([v['hop_um'] for v in info.values()] or [0])
            cands.append({'delta': d, 'proxy': round(s, 1), 'eval': {k: v for k, v in r.items() if not k.startswith('_')},
                          'stations': info, 'max_hop': maxhop, 'new_legal_errors': errs})
        cands.sort(key=lambda c: (bool(c['new_legal_errors']), c['max_hop'] > REACH, c['eval']['overflow'], c['eval']['bitmm']))
        # street re-allocation around the 2 best legal arrangements
        for c0 in [c for c in cands if not c['new_legal_errors'] and c['max_hop'] <= REACH][:2]:
            for gv, d in geom_variants(ty, c0['delta']):
                st = ty.place(d)
                regs, info = restation(ty, st)
                pts = [('ist ' + k, v) for k, v in regs.items()] + [('ft ' + k, v) for k, v in ty.fixed_soft.items() if k.startswith('u_ft_')]
                errs = [e for e in legal(ty, st, pts) if e not in legal(ty, base, pts0)]
                if errs:
                    continue
                r = ty.evaluate(st, soft_fixed=regs)
                maxhop = max([v['hop_um'] for v in info.values()] or [0])
                cands.append({'delta': d, 'geom': gv, 'proxy': None, 'eval': {k: v for k, v in r.items() if not k.startswith('_')},
                              'stations': info, 'max_hop': maxhop, 'new_legal_errors': errs})
        cands.sort(key=lambda c: (bool(c['new_legal_errors']), c['max_hop'] > REACH, c['eval']['overflow'], c['eval']['bitmm']))
        out = {'type': a.type, 'n_configs': n, 'before': {k: v for k, v in rb.items() if not k.startswith('_')},
               'before_proxy': round(proxy(ty, base)[0], 1), 'candidates': cands}
        open(a.out, 'w').write(json.dumps(out, default=str))
        b = cands[0]
        print(a.type, 'configs', n, 'before ov', rb['overflow'], 'bitmm', rb['bitmm'], 'cutH', rb['worst_cut_Hline']['ratio'],
              'cutV', rb['worst_cut_Vline']['ratio'], '| best ov', b['eval']['overflow'], 'bitmm', b['eval']['bitmm'],
              'cutH', b['eval']['worst_cut_Hline']['ratio'], 'cutV', b['eval']['worst_cut_Vline']['ratio'], 'maxhop', b['max_hop'],
              'errs', b['new_legal_errors'], 'delta', b['delta'])
        return
    if a.cmd == 'eval':
        delta = load(a.delta).get(a.type, {}) if a.delta else None
        st = ty.place(delta)
        regs = None
        if delta:
            regs, info = restation(ty, st)
        r = ty.evaluate(st, soft_fixed=regs, keep_paths=a.paths)
        r['legal_errors'] = legal(ty, st)
        r['unmapped_rtl_hard'] = sorted(i for i in ty.cores if i not in ty.rmap.values())
        if delta:
            r['stations'] = info
        out = json.dumps(r, default=str)
        if a.out:
            open(a.out, 'w').write(out)
            rs = ty.rects(st)
            cores = []
            for i, c in ty.cores.items():
                gr = [{'bus': b, 'n': g[2], 'c': xform(st[i][0], c['outline_um'], st[i][1], g[0], g[1])}
                      for b, g in ty.groups[i].items()]
                cores.append({'inst': i, 'module': c['module'], 'rect': rs[i], 'orient': st[i][1], 'groups': gr})
            lc = ty.t.get('clock', {}).get('landing_contract') or {}
            bands = lc.get('bands') if isinstance(lc, dict) else None
            geo = {'outline': [ty.W, ty.H], 'cores': cores, 'buses': ty.t['buses'], 'tap_um': ty.t.get('clock', {}).get('tap_um'),
                   'bands': {k: v.get('rect_um') for k, v in (bands or {}).items()} if isinstance(bands, dict) else {}}
            open(a.out.replace('.json', '.geo.json'), 'w').write(json.dumps(geo, default=str))
        print(json.dumps({k: v for k, v in r.items() if not k.startswith('_')}, indent=1, default=str))


if __name__ == '__main__':
    main()
