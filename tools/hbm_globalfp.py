#!/usr/bin/env python3
"""GLOBAL-FP-H: score / generate / compare global floorplans of the HBM accelerator die on ONE objective.

Inputs: graph.json from tools/hbm_globalfp_graph.py; forward_D_geometry.json (the current v15 + D local PV
layout) and the native PC home frames.  Every candidate is scored by the same function `score`:

  length(link)   = Manhattan gap between the two outlines (closest points; 0 when abutting). Pins are not yet
                   assigned for most masters, so this is a common optimistic lower bound for every candidate.
  sum_bits_mm    = sum bits x length
  traffic_mm     = sum bytes/token x length (Qwen3-8B TP4 8K, DS-V4.1 TP96 1M)
  bits_over_500  = sum bits of links longer than 500 um (one register stage at 0.833 ns, SS 504 um)
  relay_flops    = sum bits x max(0, ceil(L/500) - 1)
  fixed_return   = LG/QUANT bank-pair links (fixed 10/7, 14/11, 18/15 returns) longer than 500 um (hard rule)
  worst_cut      = max over 1 mm segments of vertical/horizontal cut lines every 100 um of crossing bits /
                   usable tracks (M6+M8 or M7+M9 at 64/80 nm pitch x 0.5 signal share = 14.06 tracks/um; 0 over PHY);
                   each link routed half HV, half VH
  J              = sum_bits_mm/B0 + (traffic_q/TQ0 + traffic_d/TD0)/2 + relay_flops/R0 + 20 x fixed_return_bits/F
                   + 10 x max(0, worst_cut - 0.60), normalised by the CURRENT layout (J_current = 3 + penalties)
"""
import argparse, collections, copy, json, math, os, random, sys
import numpy as np

W_DIE, H_DIE = 32984.288, 25980.528
HALO = 20.0
REACH = 500.0
TRK = 14.0625          # tracks per um usable for a die-level cut (see docstring)
QS = ['SW', 'SE', 'NW', 'NE']


# ----------------------------------------------------------------------------------------------- geometry helpers
def gap(a, b):
    """closest-point Manhattan gap and the two closest points"""
    ax0, ay0, ax1, ay1 = a['x'], a['y'], a['x'] + a['w'], a['y'] + a['h']
    bx0, by0, bx1, by1 = b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h']
    def axis(a0, a1, b0, b1):
        if a1 < b0:
            return b0 - a1, a1, b0
        if b1 < a0:
            return a0 - b1, a0, b1
        m = (max(a0, b0) + min(a1, b1)) / 2
        return 0.0, m, m
    dx, pax, pbx = axis(ax0, ax1, bx0, bx1)
    dy, pay, pby = axis(ay0, ay1, by0, by1)
    return dx + dy, (pax, pay), (pbx, pby)


def overlaps(P, halo=HALO, ids=None):
    ids = ids or list(P)
    out = []
    arr = [(i, P[i]['x'], P[i]['y'], P[i]['x'] + P[i]['w'], P[i]['y'] + P[i]['h']) for i in ids]
    arr.sort(key=lambda r: r[1])
    for k, (i, x0, y0, x1, y1) in enumerate(arr):
        for (j, u0, v0, u1, v1) in arr[k + 1:]:
            if u0 >= x1 + halo - 1e-6:
                break
            if v0 < y1 + halo - 1e-6 and y0 < v1 + halo - 1e-6:
                ov = min(x1, u1) - max(x0, u0) + halo
                if ov > 1e-6:
                    out.append((i, j))
    return out


def outside(P):
    return [i for i, r in P.items() if r['x'] < -1e-6 or r['y'] < -1e-6 or r['x'] + r['w'] > W_DIE + 1e-6 or r['y'] + r['h'] > H_DIE + 1e-6]


# ----------------------------------------------------------------------------------------------- scoring
def score(G, P, ref=None, cut_detail=False):
    L = G['links']
    sb = tq = td = relay = over = 0.0
    fr_bits = fr_tot = 0
    fr_viol = []
    per = []
    cls = collections.defaultdict(lambda: [0.0, 0.0, 0.0, 0.0, 0])
    for l in L:
        d, ps, pt = gap(P[l['src']], P[l['dst']])
        b = l['bits']
        sb += b * d / 1000
        q, s = l['bytes_per_token']['qwen'], l['bytes_per_token']['ds']
        tq += q * d / 1000; td += s * d / 1000
        st = max(0, math.ceil(d / REACH) - 1) if d > 0 else 0
        relay += b * st
        if d > REACH:
            over += b
        if l.get('fixed_return'):
            fr_tot += b
            if d > REACH:
                fr_bits += b; fr_viol.append((l['id'], round(d)))
        c = cls[l['cls']]; c[0] += b * d / 1000; c[1] += q * d / 1000; c[2] += s * d / 1000; c[3] += b * st; c[4] = max(c[4], d)
        per.append((l, d, ps, pt))
    cut = cuts(P, per) if True else None
    m = dict(sum_bits_mm=sb, traffic_mm_qwen=tq, traffic_mm_ds=td, relay_flops=relay, bits_over_500=over,
             fixed_return_violation_bits=fr_bits, fixed_return_violations=len(fr_viol), fixed_return_worst=sorted(fr_viol, key=lambda r: -r[1])[:8],
             worst_cut=cut['worst'], overlaps=len(overlaps(P)), outside=len(outside(P)),
             by_class={k: dict(bits_mm=round(v[0], 1), traffic_mm_qwen=round(v[1] / 1e6, 3), traffic_mm_ds=round(v[2] / 1e6, 3),
                                relay_flops=int(v[3]), longest_um=round(v[4])) for k, v in sorted(cls.items())})
    if ref:
        m['J'] = (sb / ref['sum_bits_mm'] + (tq / ref['traffic_mm_qwen'] + td / ref['traffic_mm_ds']) / 2
                  + relay / ref['relay_flops'] + 20 * fr_bits / max(1, fr_tot) + 10 * max(0, cut['worst']['ratio'] - 0.60))
    lr = sorted([(l, d) for l, d, _, _ in per if d > 2000], key=lambda r: -r[0]['bits'] * r[1])
    m['long_returns'] = [dict(link=l['id'], cls=l['cls'], bits=l['bits'], length_um=round(d), reason=REASON.get(l['cls'], 'placement')) for l, d in lr[:25]]
    m['n_long_returns'] = len(lr)
    m['_per'] = per
    if cut_detail:
        m['cut_profile'] = cut['profile']
    return m


REASON = {
    'SM_HBM': 'SM row k of a 2x4 SM block is k x 1.71 mm from its stack PC row (SM frames cannot rotate; 8 x 11.3 mm2 per stack)',
    'HBM_K': 'PC group distance along the 8.5 mm PHY edge',
    'SM_X': 'x load reads all 8 banks of the quadrant VM slice; SM frames are 6.6 mm wide',
    'KV': 'KV group g is served by stack g%4 (interleaved) while the tile sits in one field',
    'ATT_Q': 'query front reads NE bank pairs (RG3 canonical, NE allocation)',
    'ATT_O': 'canonical WG1 output to NE banks',
    'COLL_RING': '2x2 quadrant ring seam between quadrant COLL engines',
    'VM_RING': '2x2 VM ring stop link between quadrant hubs',
    'COLL_EP': 'link endpoints sit at the SerDes shoreline',
    'EP_SERDES': 'SerDes shoreline',
    'HC_ENG': 'single NE HC arithmetic engine shared by four quadrant taps',
    'IDX_COLL': 'IDX top-k link feeds the SW COLL delivery',
    'COLL_VM': 'COLL reads/writes all 8 banks of its quadrant',
    'SM_OUT': 'SM result read back by the quadrant hub',
}


def cuts(P, per, step=100.0, seg=1000.0):
    """vertical and horizontal cut lines; demand per 1 mm segment; half HV / half VH routes"""
    nx, ny = int(W_DIE // step), int(H_DIE // step)
    nsx, nsy = int(math.ceil(H_DIE / seg)), int(math.ceil(W_DIE / seg))
    V = np.zeros((nx + 1, nsx))   # vertical line at x=i*step, segment along y
    Hh = np.zeros((ny + 1, nsy))
    phys = [(r['x'], r['y'], r['x'] + r['w'], r['y'] + r['h']) for i, r in P.items() if i.startswith('phy_')]
    def hits(a, c):      # HV route from a crosses a PHY interior?
        for (x0, y0, x1, y1) in phys:
            lo, hi = sorted((a[0], c[0]))
            if y0 + 1 < a[1] < y1 - 1 and lo < x1 - 1 and hi > x0 + 1:
                return True
            lo, hi = sorted((a[1], c[1]))
            if x0 + 1 < c[0] < x1 - 1 and lo < y1 - 1 and hi > y0 + 1:
                return True
        return False
    for l, d, ps, pt in per:
        if d <= 0:
            continue
        routes = [(ps, pt), (pt, ps)]
        okr = [r for r in routes if not hits(*r)]
        routes = okr or routes
        b = l['bits'] / len(routes)
        for (a, c) in routes:          # HV from a: horizontal at a.y to c.x, vertical at c.x
            x0, x1 = sorted((a[0], c[0]))
            i0, i1 = int(math.ceil(x0 / step)), int(math.floor(x1 / step))
            if i1 >= i0:
                V[i0:i1 + 1, min(nsx - 1, int(a[1] // seg))] += b
            y0, y1 = sorted((a[1], c[1]))
            j0, j1 = int(math.ceil(y0 / step)), int(math.floor(y1 / step))
            if j1 >= j0:
                Hh[j0:j1 + 1, min(nsy - 1, int(c[0] // seg))] += b
    # supply: zero where the segment lies inside a PHY
    supV = np.full_like(V, TRK * seg); supH = np.full_like(Hh, TRK * seg)
    for i, r in P.items():
        if not i.startswith('phy_'):
            continue
        for xi in range(int(math.ceil(r['x'] / step)), int(math.floor((r['x'] + r['w']) / step)) + 1):
            for s in range(int(r['y'] // seg), min(nsx, int((r['y'] + r['h']) // seg) + 1)):
                ovl = max(0.0, min((s + 1) * seg, r['y'] + r['h']) - max(s * seg, r['y']))
                supV[xi, s] = TRK * max(0.0, seg - ovl)
        for yj in range(int(math.ceil(r['y'] / step)), int(math.floor((r['y'] + r['h']) / step)) + 1):
            for s in range(int(r['x'] // seg), min(nsy, int((r['x'] + r['w']) // seg) + 1)):
                ovl = max(0.0, min((s + 1) * seg, r['x'] + r['w']) - max(s * seg, r['x']))
                supH[yj, s] = TRK * max(0.0, seg - ovl)
    with np.errstate(divide='ignore', invalid='ignore'):
        rV = np.where(supV > 0, V / supV, np.where(V > 0, 9.99, 0))
        rH = np.where(supH > 0, Hh / supH, np.where(Hh > 0, 9.99, 0))
    iv = np.unravel_index(np.argmax(rV), rV.shape); ih = np.unravel_index(np.argmax(rH), rH.shape)
    wv = dict(ratio=float(rV[iv]), axis='x', line_um=float(iv[0] * step), segment_um=[float(iv[1] * seg), float((iv[1] + 1) * seg)], bits=float(V[iv]))
    wh = dict(ratio=float(rH[ih]), axis='y', line_um=float(ih[0] * step), segment_um=[float(ih[1] * seg), float((ih[1] + 1) * seg)], bits=float(Hh[ih]))
    worst = wv if wv['ratio'] >= wh['ratio'] else wh
    worst = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in worst.items()}
    # whole-line bisection ratios
    bis = dict(x=float((V.sum(1) / (TRK * H_DIE)).max()), y=float((Hh.sum(1) / (TRK * W_DIE)).max()))
    worst['whole_line_max'] = {k: round(v, 3) for k, v in bis.items()}
    worst['segments_over_060'] = int((rV > 0.6).sum() + (rH > 0.6).sum())
    return dict(worst=worst, profile=dict(V=(rV.max(1)).round(3).tolist(), H=(rH.max(1)).round(3).tolist()))


# ----------------------------------------------------------------------------------------------- placement utilities
def free_spot(P, n, cx, cy, region=None, halo=HALO, step=50.0, maxr=40000):
    """nearest legal lower-left position for node n centred near (cx,cy) (spiral on a grid)"""
    w, h = n['w'], n['h']
    rx0, ry0, rx1, ry1 = region or (0, 0, W_DIE, H_DIE)
    boxes = np.array([(r['x'], r['y'], r['x'] + r['w'], r['y'] + r['h']) for r in P.values()]) if P else np.zeros((0, 4))
    def ok(x, y):
        if x < rx0 or y < ry0 or x + w > rx1 or y + h > ry1:
            return False
        if len(boxes) == 0:
            return True
        return not np.any((boxes[:, 0] < x + w + halo) & (x < boxes[:, 2] + halo) & (boxes[:, 1] < y + h + halo) & (y < boxes[:, 3] + halo))
    x0, y0 = cx - w / 2, cy - h / 2
    r = 0
    while r * step < maxr:
        cands = []
        for k in range(-r, r + 1):
            for (dx, dy) in ((k, -r), (k, r), (-r, k), (r, k)):
                cands.append((abs(dx) + abs(dy), dx, dy))
        for _, dx, dy in sorted(set(cands)):
            x, y = x0 + dx * step, y0 + dy * step
            if ok(x, y):
                return x, y
        r += 1
    raise RuntimeError(f'no spot for {n["id"]}')


def complete(G, P, order=None, regions=None):
    """greedy completion: place every unplaced node at the nearest legal spot to the bit-weighted centroid of its placed
    neighbours (the same rule for every candidate)."""
    N = G['nodes']
    adj = collections.defaultdict(list)
    for l in G['links']:
        adj[l['src']].append((l['dst'], l['bits'])); adj[l['dst']].append((l['src'], l['bits']))
    todo = [i for i in N if i not in P]
    while todo:
        def conn(i):
            return sum(b for j, b in adj[i] if j in P)
        todo.sort(key=lambda i: -conn(i))
        i = todo.pop(0)
        nb = [(j, b) for j, b in adj[i] if j in P]
        if nb:
            sw = sum(b for _, b in nb)
            cx = sum((P[j]['x'] + P[j]['w'] / 2) * b for j, b in nb) / sw
            cy = sum((P[j]['y'] + P[j]['h'] / 2) * b for j, b in nb) / sw
        else:
            cx, cy = W_DIE / 2, H_DIE / 2
        reg = (regions or {}).get(i)
        x, y = free_spot(P, N[i], cx, cy, reg)
        P[i] = dict(x=x, y=y, w=N[i]['w'], h=N[i]['h'], imputed=True)
    return P


def put(G, P, i, x, y):
    if i not in G['nodes']:        # e.g. ATT blocks of the v15/D boxes when the graph has attention on the SMs
        return
    n = G['nodes'][i]
    P[i] = dict(x=x, y=y, w=n['w'], h=n['h'])


# ----------------------------------------------------------------------------------------------- current layout
def current(G, fwd, pc_homes):
    B = json.load(open(fwd))['boxes']
    P = {}
    for q in QS:
        put(G, P, f'phy_{q}', B[f'phy_{q}']['x'], B[f'phy_{q}']['y'])
        for j in range(8):
            s = QS.index(q) * 8 + j
            put(G, P, f'sm_{q}{j}', B[f'SM{s}']['x'], B[f'SM{s}']['y'])
        for b in range(8):
            bb = B[f'VM_{q}_{b}']
            n = G['nodes'][f'vmb_{q}{b}']
            put(G, P, f'vmb_{q}{b}', bb['x'] + bb['w'] - n['w'], bb['y'])
    for k, v in B.items():
        if k.startswith('lk_'):
            put(G, P, k, v['x'], v['y'])
        if k.startswith('endpoint_'):
            put(G, P, 'ep_' + k.split('_')[1], v['x'], v['y'])
        if k.startswith('gather_plan'):
            put(G, P, 'att_g' + k[-1], v['x'], v['y'])
    t = collections.defaultdict(list)
    for k, v in B.items():
        if v['role'] == 'ATT_quad':
            t[v['logical_tile']].append(v)
    for g, qs in t.items():
        put(G, P, f'att_t{g}', min(v['x'] for v in qs), min(v['y'] for v in qs))
    fld = collections.defaultdict(list)
    for k, v in B.items():
        if k.startswith('Pfield'):
            fld[int(k[6:].split('_')[0])].append(v)
    for f, l in fld.items():
        x = sum(v['x'] for v in l) / len(l); y = sum(v['y'] for v in l) / len(l)
        put(G, P, f'att_qp{f}', x - 210, y - 210)
    put(G, P, 'att_ctl', B['ATT_programme']['x'], B['KV_metadata0']['y'])
    # native PC homes (explicit four-stack candidate homes, 340cfd747)
    H = json.load(open(pc_homes))['system_candidate_homes']
    for q in QS:
        o = H[q]['pc_origins_um']
        for j in range(8):
            pts = o[4 * j:4 * j + 4]
            put(G, P, f'pc_{q}{j}', min(p[0] for p in pts), min(p[1] for p in pts) - (54.0 if q in ('NW', 'NE') else 0))
    # remove overlaps created by the merged bank+LG and PC+svc outlines (move the later box minimally)
    P = legalize(G, P, fixed=set(k for k in P if k.startswith(('phy_', 'sm_', 'lk_'))))
    return complete(G, P)


def legalize(G, P, fixed=(), regions=None):
    """remove overlaps: keep fixed and larger boxes; re-place each conflicting smaller box at its nearest legal spot"""
    for _ in range(4):
        ov = overlaps(P)
        inreg = all(not (r and (r['x'] < rg[0] - 1 or r['y'] < rg[1] - 1 or r['x'] + r['w'] > rg[2] + 1 or r['y'] + r['h'] > rg[3] + 1))
                    for i, rg in (regions or {}).items() for r in [P.get(i)] if i not in fixed)
        if not ov and not outside(P) and inreg:
            return P
        bad = set()
        for i, j in ov:
            a, b = (i, j) if P[i]['w'] * P[i]['h'] <= P[j]['w'] * P[j]['h'] else (j, i)
            if a in fixed:
                a = b
            if a not in fixed:
                bad.add(a)
        bad |= set(i for i in outside(P) if i not in fixed)
        for i, rg in (regions or {}).items():
            r = P.get(i)
            if r and i not in fixed and (r['x'] < rg[0] - 1 or r['y'] < rg[1] - 1 or r['x'] + r['w'] > rg[2] + 1 or r['y'] + r['h'] > rg[3] + 1):
                bad.add(i)
        keep = {k: v for k, v in P.items() if k not in bad}
        for i in sorted(bad, key=lambda i: -P[i]['w'] * P[i]['h']):
            r = P[i]
            x, y = free_spot(keep, dict(G['nodes'][i], id=i), r['x'] + r['w'] / 2, r['y'] + r['h'] / 2, (regions or {}).get(i), step=25.0)
            keep[i] = dict(r, x=x, y=y, moved_by_legalize=True)
        P = keep
    return P


# ----------------------------------------------------------------------------------------------- annealer
class Annealer:
    """simulated annealing over continuous positions: cost = normalised bits*L + traffic*L + relay stages
    + fixed-return reach penalty + overlap area penalty.  PHYs fixed; SerDes slide along their shoreline."""

    def __init__(self, G, P, ref, regions=None, seed=1, w_overlap=5.0, groups=None):
        self.G, self.ref = G, ref
        self.groups = groups
        self.ids = list(G['nodes'])
        self.ix = {i: k for k, i in enumerate(self.ids)}
        N = G['nodes']
        self.x = np.array([P[i]['x'] for i in self.ids]); self.y = np.array([P[i]['y'] for i in self.ids])
        self.w = np.array([N[i]['w'] for i in self.ids]); self.h = np.array([N[i]['h'] for i in self.ids])
        self.fixed = np.array([N[i]['fixed'] for i in self.ids])
        self.kind = [N[i]['kind'] for i in self.ids]
        self.regions = regions or {}
        self.reg = np.array([self.regions.get(i, (0, 0, W_DIE, H_DIE)) for i in self.ids], dtype=float)
        L = G['links']
        self.ls = np.array([self.ix[l['src']] for l in L]); self.ld = np.array([self.ix[l['dst']] for l in L])
        tqn = ref['traffic_mm_qwen'] * 1000; tdn = ref['traffic_mm_ds'] * 1000
        self.lb = np.array([l['bits'] for l in L], float)
        self.lw = (self.lb / (ref['sum_bits_mm'] * 1000) + 0.5 * np.array([l['bytes_per_token']['qwen'] for l in L]) / tqn
                   + 0.5 * np.array([l['bytes_per_token']['ds'] for l in L]) / tdn)
        self.lr = self.lb / ref['relay_flops']
        self.lf = np.array([20.0 / 17792 / 3 if l.get('fixed_return') else 0.0 for l in L])
        self.inc = collections.defaultdict(list)
        for k, l in enumerate(L):
            self.inc[self.ix[l['src']]].append(k); self.inc[self.ix[l['dst']]].append(k)
        self.inc = {k: np.array(v) for k, v in self.inc.items()}
        self.wo = w_overlap
        self.rng = random.Random(seed)
        self.np_rng = np.random.default_rng(seed)

    def lcost(self, ks, x, y):
        s, d = self.ls[ks], self.ld[ks]
        ax0, ay0, aw, ah = x[s], y[s], self.w[s], self.h[s]
        bx0, by0, bw, bh = x[d], y[d], self.w[d], self.h[d]
        dx = np.maximum(0, np.maximum(bx0 - (ax0 + aw), ax0 - (bx0 + bw)))
        dy = np.maximum(0, np.maximum(by0 - (ay0 + ah), ay0 - (by0 + bh)))
        L = dx + dy
        st = np.maximum(0, np.ceil(L / REACH) - 1)
        return self.lw * 0 if False else (self.lw[ks] * L + self.lr[ks] * st + self.lf[ks] * np.maximum(0, L - REACH + 50) / 50 * (L > REACH - 50))

    def ocost(self, i, xi, yi):
        x0 = np.maximum(self.x, xi - HALO) ; x1 = np.minimum(self.x + self.w, xi + self.w[i] + HALO)
        y0 = np.maximum(self.y, yi - HALO) ; y1 = np.minimum(self.y + self.h, yi + self.h[i] + HALO)
        ov = np.clip(x1 - x0, 0, None) * np.clip(y1 - y0, 0, None)
        ov[i] = 0
        r = self.reg[i]
        out = max(0, r[0] - xi) + max(0, xi + self.w[i] - r[2]) + max(0, r[1] - yi) + max(0, yi + self.h[i] - r[3])
        return self.wo * ov.sum() / 1e6 + self.wo * out / 10.0

    def total(self):
        ks = np.arange(len(self.ls))
        c = self.lcost(ks, self.x, self.y).sum()
        o = sum(self.ocost(i, self.x[i], self.y[i]) for i in range(len(self.ids))) / 2
        return c, o

    def run(self, iters=200000, t0=0.02, t1=0.00002, step0=3000.0, step1=30.0, log=None, only=None, swap_only=()):
        mov = [i for i in range(len(self.ids)) if not self.fixed[i] and (only is None or self.ids[i] in only or self.ids[i] in swap_only)]
        swo = set(self.ix[i] for i in swap_only)
        same = collections.defaultdict(list)
        self.qd = [self.G['nodes'][i]['quadrant'] if self.G['nodes'][i]['kind'] in ('SM', 'PC') else None for i in self.ids]
        for i in mov:
            same[(self.kind[i], round(self.w[i]), round(self.h[i]), self.qd[i])].append(i)
        acc = 0
        movset = set(mov) - set(self.ix[i] for i in swap_only)
        groups = [[self.ix[i] for i in g if i in self.ix and self.ix[i] in movset] for g in (self.groups or [])]
        groups = [g for g in groups if len(g) > 1]
        for it in range(iters):
            f = it / iters
            T = t0 * (t1 / t0) ** f
            stp = step0 * (step1 / step0) ** f
            if groups and self.rng.random() < 0.08:
                g = np.array(groups[self.rng.randrange(len(groups))])
                ks = np.unique(np.concatenate([self.inc.get(int(i), np.zeros(0, int)) for i in g])).astype(int)
                ddx, ddy = self.np_rng.normal() * stp * 1.5, self.np_rng.normal() * stp * 1.5
                before = self.lcost(ks, self.x, self.y).sum() + sum(self.ocost(int(i), self.x[i], self.y[i]) for i in g)
                self.x[g] += ddx; self.y[g] += ddy
                after = self.lcost(ks, self.x, self.y).sum() + sum(self.ocost(int(i), self.x[i], self.y[i]) for i in g)
                d = after - before
                if d < 0 or self.rng.random() < math.exp(-d / T):
                    acc += 1
                else:
                    self.x[g] -= ddx; self.y[g] -= ddy
                continue
            i = mov[self.rng.randrange(len(mov))]
            grp = same[(self.kind[i], round(self.w[i]), round(self.h[i]), self.qd[i])]
            if (i in swo or self.rng.random() < 0.15) and len(grp) > 1:
                j = grp[self.rng.randrange(len(grp))]
                if j == i:
                    continue
                ks = np.unique(np.concatenate([self.inc.get(i, np.zeros(0, int)), self.inc.get(j, np.zeros(0, int))])).astype(int)
                before = self.lcost(ks, self.x, self.y).sum() + self.ocost(i, self.x[i], self.y[i]) + self.ocost(j, self.x[j], self.y[j])
                nx, ny = self.x.copy(), self.y.copy()
                nx[i], nx[j], ny[i], ny[j] = self.x[j], self.x[i], self.y[j], self.y[i]
                ox, oy = self.x, self.y
                self.x, self.y = nx, ny
                after = self.lcost(ks, nx, ny).sum() + self.ocost(i, nx[i], ny[i]) + self.ocost(j, nx[j], ny[j])
                d = after - before
                if d < 0 or self.rng.random() < math.exp(-d / T):
                    acc += 1
                else:
                    self.x, self.y = ox, oy
                continue
            ks = self.inc.get(i, np.zeros(0, int))
            xi, yi = self.x[i], self.y[i]
            if self.kind[i] == 'SERDES':
                nxi, nyi = xi + self.np_rng.normal() * stp, yi
            else:
                nxi, nyi = xi + self.np_rng.normal() * stp, yi + self.np_rng.normal() * stp
            before = (self.lcost(ks, self.x, self.y).sum() if len(ks) else 0) + self.ocost(i, xi, yi)
            self.x[i], self.y[i] = nxi, nyi
            after = (self.lcost(ks, self.x, self.y).sum() if len(ks) else 0) + self.ocost(i, nxi, nyi)
            d = after - before
            if d < 0 or self.rng.random() < math.exp(-d / T):
                acc += 1
            else:
                self.x[i], self.y[i] = xi, yi
            if log and it % (iters // 10) == 0:
                c, o = self.total()
                print(f'  it {it} T {T:.2e} step {stp:.0f} wire {c:.4f} overlap {o:.4f} acc {acc}', file=log, flush=True)
        return self

    def placement(self):
        return {i: dict(x=float(self.x[k]), y=float(self.y[k]), w=float(self.w[k]), h=float(self.h[k])) for k, i in enumerate(self.ids)}


# ----------------------------------------------------------------------------------------------- architect topologies
def mirror(q, x, y, w, h):
    if q in ('SE', 'NE'):
        x = W_DIE - x - w
    if q in ('NW', 'NE'):
        y = H_DIE - y - h
    return x, y


def arch_spine(G, ne_vm='spine', att='centre', kv='interleave', hc='single'):
    """architect topology: per stack, PC row on the PHY, 2x4 SM block split by a vertical VM spine that holds the
    compact 8-bank slice with its LG chains, every engine's bank-pair port groups, hub/delivery and COLL; SerDes
    + endpoints in the inter-PHY shoreline gap; ATT, IDX, HC engine in the centre band."""
    N = G['nodes']; P = {}
    phy = {'SW': (1455.84, 21.6), 'SE': (22165.712, 21.6), 'NW': (1455.84, H_DIE - 1198.8), 'NE': (22165.712, H_DIE - 1198.8)}
    for q in QS:
        put(G, P, f'phy_{q}', *phy[q])
    spine_w = 2 * N['vmb_SW0']['w'] + 3 * HALO
    for q in QS:
        # PC row along the PHY
        for j in range(8):
            x = 1455.84 + 8 + j * (N['pc_SW0']['w'] + HALO)
            y = 1198.8 + HALO
            P[f'pc_{q}{j}'] = dict(zip(('x', 'y'), mirror(q, x, y, N['pc_SW0']['w'], N['pc_SW0']['h'])), w=N['pc_SW0']['w'], h=N['pc_SW0']['h'])
        y0 = 1198.8 + HALO + N['pc_SW0']['h'] + HALO
        xl = 150.0; xr = xl + 6609.6 + HALO + spine_w + HALO
        # SM j: rows r=j//2, left/right col = j%2; PCs of SM j sit under col
        for j in range(8):
            r, c = j // 2, j % 2
            x = xl if c == 0 else xr
            y = y0 + r * (1712.08 + HALO + 10)
            P[f'sm_{q}{j}'] = dict(zip(('x', 'y'), mirror(q, x, y, 6609.6, 1712.08)), w=6609.6, h=1712.08)
        sx = xl + 6609.6 + HALO
        # VM banks: 2 columns x 4 rows in the spine centred on SM rows 1..2
        ybank0 = y0 + 2 * (1712.08 + 30) - 2 * (N[f'vmb_{q}0']['h'] + HALO)
        for b in range(8):
            c, r = b % 2, b // 2
            n = N[f'vmb_{q}{b}']
            x = sx + c * (n['w'] + HALO)
            y = ybank0 + r * (n['h'] + HALO)
            if not (q == 'NE' and ne_vm != 'spine'):
                P[f'vmb_{q}{b}'] = dict(zip(('x', 'y'), mirror(q, x, y, n['w'], n['h'])), w=n['w'], h=n['h'])
        P_regions = None
    # SerDes and endpoints in the inter-PHY shoreline gap
    for side, ls in (('S', ['S0', 'S1', 'S2', 'S3', 'S4']), ('N', ['N0', 'N1', 'N2', 'N3'])):
        n = len(ls)
        tot = n * 250.056 + (n - 1) * 40
        x0 = W_DIE / 2 - tot / 2
        for k, l in enumerate(ls):
            x = x0 + k * (250.056 + 40)
            y = 20.0 if side == 'S' else H_DIE - 20 - 2250.216
            put(G, P, f'lk_{l}', x, y)
    return P


REGION_Q = {'SW': (0, 0, W_DIE / 2, H_DIE / 2), 'SE': (W_DIE / 2, 0, W_DIE, H_DIE / 2),
            'NW': (0, H_DIE / 2, W_DIE / 2, H_DIE), 'NE': (W_DIE / 2, H_DIE / 2, W_DIE, H_DIE)}


def arch_template(G, colgap=20.0, band_after=None, band_h=0.0, xmode='edge', pcmode='row', sym=True):
    """architect template: per stack a 2-column x 4-row SM block (R0/MY), a vertical gap of `colgap` between the
    columns (the VM spine when > 0.9 mm), an optional horizontal band of `band_h` after SM row `band_after`
    (the VM band), the block either at the die edge (xmode='edge') or hugging the die centre line ('centre');
    PC groups in one row on the PHY; SerDes/endpoints in the inter-PHY shoreline gap."""
    N = G['nodes']; P = {}
    phy = {'SW': (1455.84, 21.6), 'SE': (22165.712, 21.6), 'NW': (1455.84, H_DIE - 1198.8), 'NE': (22165.712, H_DIE - 1198.8)}
    for q in QS:
        put(G, P, f'phy_{q}', *phy[q])
    smw, smh = 6609.6, 1712.08
    blockw = 2 * smw + colgap
    for q in QS:
        pw, ph = N['pc_SW0']['w'], N['pc_SW0']['h']
        for j in range(8):
            x = 1455.84 + 2 + j * (pw + HALO + 0.5)
            y = 1198.8 + HALO
            P[f'pc_{q}{j}'] = dict(zip(('x', 'y'), mirror(q, x, y, pw, ph)), w=pw, h=ph)
        y0 = 1198.8 + HALO + ph + HALO
        x0 = 120.0 if xmode == 'edge' else W_DIE / 2 - 800.0 - blockw   # centre: 1.6 mm channel keeps the 5-wide SerDes shoreline clear
        for j in range(8):
            r, c = j // 2, j % 2
            x = x0 + c * (smw + colgap)
            y = y0 + r * (smh + HALO) + (band_h if band_after is not None and r >= band_after else 0.0)
            P[f'sm_{q}{j}'] = dict(zip(('x', 'y'), mirror(q, x, y, smw, smh)), w=smw, h=smh)
    for side, ls in (('S', ['S0', 'S1', 'S2', 'S3', 'S4']), ('N', ['N0', 'N1', 'N2', 'N3'])):
        n = len(ls); tot = n * 250.056 + (n - 1) * 40
        for k, l in enumerate(ls):
            x = W_DIE / 2 - tot / 2 + k * (250.056 + 40)
            y = 20.0 if side == 'S' else H_DIE - 20 - 2250.216
            put(G, P, f'lk_{l}', x, y)
    return P


SHORE = {'S': (9955.9 + 20, 0, 22165.712 - 20, 2400.0), 'N': (9955.9 + 20, H_DIE - 2400.0, 22165.712 - 20, H_DIE)}
H_DIE_V15 = H_DIE


def set_die(h):
    """die outline height (um): the v15 outline by default; a compact-outline candidate (ATT area freed) passes a smaller
    height. Width is fixed by the two PHY edges + SerDes shoreline. Module-level regions follow."""
    global H_DIE, REGION_Q, SHORE
    H_DIE = float(h)
    REGION_Q = {'SW': (0, 0, W_DIE / 2, H_DIE / 2), 'SE': (W_DIE / 2, 0, W_DIE, H_DIE / 2),
                'NW': (0, H_DIE / 2, W_DIE / 2, H_DIE), 'NE': (W_DIE / 2, H_DIE / 2, W_DIE, H_DIE)}
    SHORE = {'S': (9955.9 + 20, 0, 22165.712 - 20, 2400.0), 'N': (9955.9 + 20, H_DIE - 2400.0, 22165.712 - 20, H_DIE)}


def shoreline_regions(G):
    return {i: SHORE[i[3]] for i in G['nodes'] if i.startswith('lk_')}


def default_groups(G):
    N = G['nodes']; g = []
    for q in QS:
        g.append([i for i, n in N.items() if n['quadrant'] == q and n['kind'] in ('VM_bank', 'SU', 'SFU', 'HC', 'VM_hub', 'COLL', 'QUANT')])
        g.append([i for i, n in N.items() if n['quadrant'] == q and n['kind'] in ('VM_bank', 'SU', 'SFU', 'HC')])
    for f in range(4):
        g.append([f'att_t{t}' for t in range(32) if t % 4 == f] + [f'att_qp{f}', f'att_g{f}'])
    g.append([i for i in N if i.startswith('att_')])
    g.append([i for i in N if i.startswith('idx_')])
    return g


def quadrant_regions(G, which=('SM', 'PC')):
    return {i: REGION_Q[n['quadrant']] for i, n in G['nodes'].items() if n['kind'] in which and n['quadrant']}


# ----------------------------------------------------------------------------------------------- output
COLORS = {'SM': '#f2c18d', 'PHY': '#8c8c8c', 'PC': '#c9b37a', 'VM_bank': '#2f6fb0', 'VM_hub': '#6fa0d8', 'SU': '#3b9b4a', 'SFU': '#7cc06f',
          'HC': '#1f6b2f', 'HC_ENGINE': '#0d4d1c', 'QUANT': '#b0d36a', 'COLL': '#8e44ad', 'SERDES': '#5b2c83', 'ENDPOINT': '#b07cc6',
          'ATT_tile': '#e0703a', 'ATT_gather': '#d62728', 'ATT_QP': '#9ecae1', 'ATT_reduce': '#c0392b', 'ATT_ctl': '#555', 'IDX': '#17becf'}
LCOL = {'SM_HBM': '#b8860b', 'HBM_K': '#b8860b', 'SM_X': '#1f77b4', 'KV': '#e377c2', 'ATT_Q': '#d62728', 'ATT_O': '#d62728', 'COLL_RING': '#8e44ad',
        'VM_RING': '#2f6fb0', 'COLL_EP': '#8e44ad', 'HC_ENG': '#0d4d1c', 'COLL_VM': '#8e44ad', 'IDX_VM': '#17becf', 'IDX_COLL': '#17becf'}


def svg(G, P, m, title, path, scale=0.022, top=300):
    W, H = W_DIE * scale, H_DIE * scale
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.1f} {H:.1f}" width="{W:.0f}" height="{H:.0f}" font-family="sans-serif">',
         f'<rect x="0" y="0" width="{W:.1f}" height="{H:.1f}" fill="#fbfbf8" stroke="#333" stroke-width="1"/>']
    Y = lambda y: H - y * scale
    for i, r in sorted(P.items(), key=lambda kv: -kv[1]['w'] * kv[1]['h']):
        k = G['nodes'][i]['kind']
        o.append(f'<rect x="{r["x"]*scale:.2f}" y="{Y(r["y"]+r["h"]):.2f}" width="{r["w"]*scale:.2f}" height="{r["h"]*scale:.2f}" '
                 f'fill="{COLORS.get(k, "#ccc")}" stroke="#222" stroke-width="0.3" fill-opacity="{0.55 if k == "SM" else 0.9}"><title>{i} ({k}) '
                 f'{r["w"]:.0f}x{r["h"]:.0f} um at ({r["x"]:.0f},{r["y"]:.0f}){" imputed" if r.get("imputed") else ""}</title></rect>')
        if k in ('SM', 'PHY'):
            o.append(f'<text x="{(r["x"]+r["w"]/2)*scale:.1f}" y="{Y(r["y"]+r["h"]/2)+3:.1f}" font-size="8" text-anchor="middle" fill="#333">{i}</text>')
    per = sorted([p for p in m['_per'] if p[1] > REACH], key=lambda p: -p[0]['bits'] * p[1])[:top]
    for l, d, ps, pt in per:
        c = LCOL.get(l['cls'], '#444')
        sw = max(0.3, min(3.0, l['bits'] / 700))
        o.append(f'<path d="M{ps[0]*scale:.1f},{Y(ps[1]):.1f} L{pt[0]*scale:.1f},{Y(ps[1]):.1f} L{pt[0]*scale:.1f},{Y(pt[1]):.1f}" fill="none" '
                 f'stroke="{c}" stroke-width="{sw:.2f}" stroke-opacity="0.55"><title>{l["id"]} {l["bits"]} b {d:.0f} um</title></path>')
    o.append('</svg>')
    open(path, 'w').write('\n'.join(o))


def links_json(G, P, m, name, path, meta=None):
    nodes = []
    for i, n in G['nodes'].items():
        r = P[i]
        nodes.append(dict(id=i, kind=n['kind'], quadrant=n['quadrant'], x=round(r['x'], 3), y=round(r['y'], 3), w=n['w'], h=n['h'],
                          orient='R0', area_mm2=n['area_mm2'], area_src=n['area_src'], fixed=n['fixed'], imputed=bool(r.get('imputed')),
                          provenance=n['provenance']))
    links = []
    for l, d, ps, pt in m['_per']:
        links.append(dict(id=l['id'], src=l['src'], dst=l['dst'], cls=l['cls'], bits=l['bits'], bytes_per_token=l['bytes_per_token'],
                          criticality=l['criticality'], provenance=l['provenance'], length_um=round(d, 1),
                          relays=max(0, math.ceil(d / REACH) - 1) if d > 0 else 0, over_500um=d > REACH,
                          fixed_return=bool(l.get('fixed_return')), src_pt=[round(ps[0], 1), round(ps[1], 1)], dst_pt=[round(pt[0], 1), round(pt[1], 1)]))
    mm = {k: v for k, v in m.items() if not k.startswith('_')}
    out = dict(schema='opentallas.dataflow.links.v1', die='hbm', candidate=name, die_outline_um=[W_DIE, H_DIE],
               units=dict(length='um', traffic='bytes_per_token'), workloads=G['inputs'], nodes=nodes, links=links, metrics=mm, meta=meta or {})
    json.dump(out, open(path, 'w'))


# ----------------------------------------------------------------------------------------------- data-flow explorer record
TOKEN_CLASS_MAP = {   # die block kind -> token-path operator classes it executes / serves (hbm_gen_qwen, hbm_gen_ds)
    'SM': ['SM'], 'PC': ['SM', 'DMA', 'ATT'], 'PHY': ['SM', 'DMA', 'ATT'], 'VM_bank': ['SM', 'SU', 'FUSED', 'SFU', 'HC', 'COLL', 'DMA', 'ATT', 'IDX', 'ARGMAX'],
    'VM_hub': ['DMA', 'COLL', 'SM'], 'SU': ['SU', 'FUSED', 'ARGMAX'], 'SFU': ['SFU'], 'HC': ['HC', 'FUSED'], 'HC_ENGINE': ['HC'],
    'QUANT': ['FUSED'], 'COLL': ['COLL'], 'ENDPOINT': ['COLL'], 'SERDES': ['COLL'], 'ATT_tile': ['ATT'], 'ATT_gather': ['ATT'],
    'ATT_QP': ['ATT'], 'ATT_reduce': ['ATT'], 'ATT_ctl': ['ATT'], 'IDX': ['IDX'],
}


TOKEN_CLASS_MAP_SM = dict(TOKEN_CLASS_MAP, SM=['SM', 'ATT'], SU=['SU', 'FUSED', 'ARGMAX', 'ATT'], PC=['SM', 'DMA', 'ATT'],
                          VM_hub=['DMA', 'COLL', 'SM', 'ATT'])
for _k in ('ATT_tile', 'ATT_gather', 'ATT_QP', 'ATT_reduce', 'ATT_ctl'):
    TOKEN_CLASS_MAP_SM.pop(_k, None)


def explorer_record(G, P, m, rid, label, note, log, base='hbm_v15_compact', inputs=None):
    names = list(G['nodes'])
    sm_att = (G.get('attention') or {}).get('mode') == 'sm'
    ix = {k: i for i, k in enumerate(names)}
    N = G['nodes']
    B = dict(name=names, master=[N[k]['kind'] for k in names], kind=[N[k]['kind'] for k in names],
             group=[(N[k]['quadrant'] or ('ATT' if k.startswith('att_') else 'die')) for k in names], reg=[0] * len(names),
             x=[round(P[k]['x'], 3) for k in names], y=[round(P[k]['y'], 3) for k in names], w=[N[k]['w'] for k in names], h=[N[k]['h'] for k in names])
    links = []
    for l, d, ps, pt in m['_per']:
        t = 8 * (l['bytes_per_token']['qwen'] + l['bytes_per_token']['ds']) / 2
        links.append(dict(i=l['id'], c=l['cls'], b=l['bits'], d=1,
                          e=[[ix[l['src']], None, round(ps[0], 1), round(ps[1], 1), 'box'], [ix[l['dst']], None, round(pt[0], 1), round(pt[1], 1), 'box']],
                          s=None, n=l['provenance'], t=round(t), cr=l['criticality'],
                          tq=round(8 * l['bytes_per_token']['qwen']), td=round(8 * l['bytes_per_token']['ds'])))
    return dict(schema='opentallas.dataflow.links.v1', id=rid, label=label, design='hbm', token_designs=['hbm_gen_qwen', 'hbm_gen_ds'],
                revision='v15-globalfp-noatt' if sm_att else 'v15-globalfp', role='candidate', scope='GLOBAL-FP-H block-level global floorplan candidate (%d-node die graph%s)' % (len(names), ', attention on SM engines, no ATT tiles' if sm_att else ''),
                outline=[W_DIE, round(H_DIE, 3)], reach_um=REACH, reach_source='0.833 ns stage, SS 504 um (ss-wire-reach) rounded to 500',
                stages_explicit=False, registers='relay stages not placed: needed stages = ceil(L/500)-1 (lower bound)',
                direction='driver first (graph source)', pins='pins unassigned: ends are closest outline points (box), lengths are lower bounds',
                token_class_map=TOKEN_CLASS_MAP_SM if sm_att else TOKEN_CLASS_MAP,
                attention=G.get('attention'),
                traffic_note='t = mean of Qwen3-8B TP4 8K and DS-V4.1 TP96 1M bits/token (tq, td separately); cr = token-path critical share of the owning class (0..1)',
                candidate=dict(of=base, agent='GLOBAL-FP-H', name=rid, note=note, log=log),
                provenance=dict(inputs=inputs or []), blocks=B, links=links)
