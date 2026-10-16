#!/usr/bin/env python3
"""S81 hub compaction screen (S-DIE-HUB, owner order 2026-10-16 07:30): one estimator for the before / after hub layouts.

PLANNING SCREEN (no GEN / GRT).  Inputs:
  * the die model of an actual GEN (tools/budgets/extract_die.py output, e.g. c26b/clock/model.json.gz): every die bus
    with its bit width.  Transport instances (stn / hstn / hend / xstg / lkck) are contracted as in
    tools/s81/global_fp/graph.py, so every block-to-block flow is one edge (p2p: summed lane widths; field trees: one
    leaf per frame, the frame's cfifo is its die port).  The field, links, PHY/CTRL/SVC band and the bus widths are
    taken from that model unchanged;
  * one or more --hub-layout JSONs (tools/s81/wide_hub_layout.py): the hub blocks (and MIX4, and the band blocks when
    the layout carries 'band_blocks') move to the layout, everything else stays where the model has it.
Per flow: the route is tools/s81/hub_router.route (the generator's own vmc router: faces toward the peer, assigned faces
for record-fixed ports, A* around every hub macro); length L -> bit-mm and relay stages ceil(L / 500 um) - 1 (the owner's
500-um hop).  Field trees: per leaf the Manhattan distance frame port -> root face point (the field is unchanged; the
root face moves); worst leaf -> stages, sum(leaf bits x distance) -> bit-mm.
Cuts: every p2p flow is split into <= 256-b bundles spread over its face window and maze-routed on an 86.4-um gcell grid
over the hub with negotiated congestion (as tools/s81/hub_grt_screen.py: H edges M4+M6 36.46 t/um, V edges M3+M5
48.61 t/um, -10 % PG/clock); field trunks enter at the hub edge at the median leaf height of their side.  Reported:
max gcell-edge utilisation (= bits per um / tracks per um) overall and per named channel.

  python3 tools/s81/hub_compact_screen.py --model model.json.gz --layout before=L0.json --layout after=L1.json --out S.json
"""
from __future__ import annotations

import argparse
import collections
import gzip
import heapq
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hub_router as HR  # noqa: E402

TRANSPORT = {'stn', 'hstn', 'hend', 'xstg', 'lkck'}
NONDATA = {'fclk', 'clock', 'reset', 'col_clock', 'col_reset'}
HOP = 500.0
G = 86.4
BUNDLE = 256
PGF = 0.90
T_EW, T_NS = 1 / 0.048 + 1 / 0.064, 1 / 0.036 + 1 / 0.048
CAP_H, CAP_V = G * T_EW * PGF, G * T_NS * PGF
DIE = (0.0, 0.0, 33000.0, 26000.0)
HCP_ROW = ('hcp_row', 9417.6, 24624.0, 10800.0, 1296.0)
# record-fixed (closed / assigned) port faces in master coordinates; everything else is generator-laid toward the peer
FIXED_FACE = {('sp_capture', 'sp_vm'): 'S', ('sp_capture', 'sp_gather'): 'N', ('sp_gather', 'sp_capture'): 'S',
              ('sp_gather', 'sp_vm'): 'E', ('sp_pq', 'sp_vm'): 'E', ('sp_pq', 'pq_cnt'): 'S',
              ('bk_selector', 'sp_vm'): 'N', ('bk_selector', 'svc_SW'): 'W', ('bk_selector', 'sp_sseq'): 'E',
              ('bk_collector', 'sp_vm'): 'S', ('bk_collector', 'svc_SW'): 'W', ('bk_collector', 'sp_sseq'): 'E',
              ('sp_wfc', '*'): 'E', ('sp_host', '*'): 'E', ('sp_sseq', '*'): 'E', ('sp_su_s', 'sp_vm'): 'N',
              ('sp_hc_s', 'sp_hc_t'): 'S', ('sp_hc_t', 'sp_hc_s'): 'N', ('svc_SW', '*'): 'N'}


def load(p):
    b = Path(p).read_bytes()
    return json.loads(gzip.decompress(b) if str(p).endswith('.gz') else b)


def flows_of(model):
    """contracted block-level flows of the model: p2p {(a, b): bits} and trees [(root, {frame: bits}, width)]"""
    ins = {i[0]: i for i in model['insts']}

    def blk(n):
        i = ins[n]
        if i[3].startswith('frame_'):
            return 'F' + i[3][6:]
        if n.startswith('pqrom'):
            return 'sp_pq'
        if n.startswith('pq_cnt'):
            return 'pq_cnt'
        return n
    par = {}

    def f(x):
        while par.setdefault(x, x) != x:
            par[x] = par[par[x]]
            x = par[x]
        return x
    B = [b for b in model['buses'] if b[1] not in NONDATA and all(e[0] in ins for e in b[3])]
    for b in B:
        tr = [e[0] for e in b[3] if ins[e[0]][2] in TRANSPORT]
        for t in tr[1:]:
            par[f(tr[0])] = f(t)
    comp = collections.defaultdict(lambda: dict(blocks=collections.Counter(), w=0))
    p2p = collections.Counter()
    for b in B:
        tr = [e[0] for e in b[3] if ins[e[0]][2] in TRANSPORT]
        real = [blk(e[0]) for e in b[3] if ins[e[0]][2] not in TRANSPORT]
        if tr:
            c = comp[f(tr[0])]
            for r in real:
                c['blocks'][r] += b[2]
            c['w'] = max(c['w'], b[2])
        else:
            rs = tuple(sorted(set(real)))
            if len(rs) == 2 and not any(r.startswith('F') for r in rs):
                p2p[rs] += b[2]
    trees = []
    for c in comp.values():
        fr = {k: v for k, v in c['blocks'].items() if k.startswith('F')}
        hb = sorted(k for k in c['blocks'] if not k.startswith('F'))
        if fr and len(hb) == 1:
            trees.append((hb[0], fr, c['w']))
        elif not fr and len(hb) >= 2:
            for i, a in enumerate(hb):
                for b in hb[i + 1:]:
                    if len(hb) == 2 or 'sp_sseq' in (a, b):
                        p2p[(a, b)] += c['w']
    ports = {}
    for i in model['insts']:
        if i[2] == 'cfifo':
            ports['F' + i[3][6:]] = (i[5] + i[7] / 2, i[6] + i[8] / 2)
    rects = {i[0]: (i[5], i[6], i[7], i[8]) for i in model['insts']
             if i[2] in ('hub', 'band_blk', 'phy', 'ctrl', 'svc', 'svcj', 'link')}
    pqc = [(i[5], i[6], i[7], i[8]) for i in model['insts'] if i[2] == 'pqcnt']
    if pqc:
        x0, y0 = min(r[0] for r in pqc), min(r[1] for r in pqc)
        rects['pq_cnt'] = (x0, y0, max(r[0] + r[2] for r in pqc) - x0, max(r[1] + r[3] for r in pqc) - y0)
    return p2p, trees, ports, rects


PORT_OF = {'sp_vm': 'vd', 'svc_SW': 'cSW', 'sp_sseq': 'c_cmd'}


def band_faces(L):
    """record faces of moved band blocks (layout 'band_blocks' [x, y, w, h, orient, {port: face}])"""
    out = {}
    for k, v in ((L or {}).get('band_blocks') or {}).items():
        fc = v[5] if len(v) > 5 else {}
        for peer, port in PORT_OF.items():
            if port == 'cSW' and k == 'bk_selector':
                port = 'iSW'
            if port in fc:
                out[(k, peer)] = fc[port]
    return out


def layout_rects(model_rects, L):
    R = dict(model_rects)
    if L is None:
        return R
    for k, v in L['blocks'].items():
        if k.startswith('bk_') and not L.get('band_blocks'):
            continue            # the generator places the band blocks itself unless the layout carries them
        R[k] = tuple(v[:4])
    for k, v in (L.get('band_blocks') or {}).items():
        R[k] = tuple(v[:4])
    if L.get('mix4_slot'):
        R['mix4'] = tuple(L['mix4_slot'][:4])
    if 'sp_capture' in R and 'pq_cnt' in R and 'sp_gather' in R:
        g, c = R['sp_gather'], R['pq_cnt']
        R['pq_cnt'] = (g[0], g[1] - 2.16 - c[3], c[2], c[3])
    return R


def ns(name, r, orient='R0'):
    return SimpleNamespace(name=name, x=r[0], y=r[1], w=r[2], h=r[3], orient=orient)


def boxes_of(R):
    return [(k, *v) for k, v in R.items() if k not in ('pq_cnt',)] + [HCP_ROW]


def end_of(R, a, b, toward=None):
    """(face, point) of a's end of the a-b flow: the record face when fixed, else the face toward the peer; the point
    is the face point nearest `toward` (the other end's point, as the generator aligns a free end) or the peer"""
    fa = FIXED_FACE.get((a, b)) or FIXED_FACE.get((a, '*'))
    ia, ib = ns(a, R[a]), ns(b, R[b])
    tw = SimpleNamespace(x=toward[0], y=toward[1], w=0.0, h=0.0) if toward else ib
    f = fa or HR.face_toward(ia, ib)
    return f, HR.face_point(ia, f, None, tw)


def plen(p):
    return sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(p, p[1:]))


def stages(L):
    return max(0, math.ceil(L / HOP - 1e-9) - 1)


def p2p_rows(R, p2p, faces=None):
    rows = []
    bx = boxes_of(R)
    saved = dict(FIXED_FACE)
    FIXED_FACE.update(faces or {})
    try:
        return _p2p_rows(R, p2p, bx)
    finally:
        FIXED_FACE.clear()
        FIXED_FACE.update(saved)


def _p2p_rows(R, p2p, bx):
    rows = []
    for (a, b), bits in sorted(p2p.items(), key=lambda kv: -kv[1]):
        if a not in R or b not in R:
            continue
        fixa = bool(FIXED_FACE.get((a, b)) or FIXED_FACE.get((a, '*')))
        fixb = bool(FIXED_FACE.get((b, a)) or FIXED_FACE.get((b, '*')))
        if fixb and not fixa:
            fb, pb = end_of(R, b, a)
            fa, pa = end_of(R, a, b, pb)
        else:
            fa, pa = end_of(R, a, b)
            fb, pb = end_of(R, b, a, pa)
        p = HR.route(pa, fa, pb, fb, bx, DIE, skip=(a, b))
        if p is None:
            p = [pa, (pa[0], pb[1]), pb]
        if len(p) > 2 and not (fixa and fixb):
            # as the generator's _vmc_path: a free (generator-laid) end tries 9 points of each of its faces; shortest
            # route that does not thread a < 2 x 21.6-um slit wins (assigned ends never move)
            best = p if not slit(p, bx, (a, b)) else None
            for fa2, pa2 in ([(fa, pa)] if fixa else samples(R[a], R[b])):
                for fb2, pb2 in ([(fb, pb)] if fixb else samples(R[b], R[a])):
                    if best is not None and abs(pa2[0] - pb2[0]) + abs(pa2[1] - pb2[1]) >= plen(best):
                        continue
                    q = HR.route(pa2, fa2, pb2, fb2, bx, DIE, skip=(a, b))
                    if q is not None and not slit(q, bx, (a, b)) and (best is None or plen(q) < plen(best)):
                        best, fa, fb = q, fa2, fb2
            p = best or p
        L = plen(p)
        rows.append(dict(a=a, b=b, bits=bits, faces=[fa, fb], len_um=round(L, 1), bit_mm=round(bits * L / 1000, 1),
                         stages=stages(L), path=[[round(x, 1), round(y, 1)] for x, y in p]))
    return rows


def samples(r, o):
    """4 points on each of the (at most 2) faces of r that look toward o"""
    x, y, w, h = r
    out = []
    fs = ('E' if o[0] + o[2] / 2 > x + w / 2 else 'W') + ('N' if o[1] + o[3] / 2 > y + h / 2 else 'S')
    for f in fs:
        span = w if f in 'NS' else h
        for k in range(1, 8, 2):
            v = 20.0 + (span - 40.0) * k / 8.0
            out.append((f, (x + v, y + h) if f == 'N' else (x + v, y) if f == 'S' else (x + w, y + v) if f == 'E'
                        else (x, y + v)))
    return out


def slit(path, boxes, skip, clr=43.2):
    """True when a segment runs inside a gap narrower than clr between two macros (its end blocks excepted)"""
    for p, q in zip(path, path[1:]):
        hor = abs(p[1] - q[1]) < 1e-6
        lo, hi = sorted((p[0], q[0]) if hor else (p[1], q[1]))
        if hi - lo < 1.0:
            continue
        c = p[1] if hor else p[0]
        below = above = False
        for n, x, y, w, h in boxes:
            if n in skip:
                continue
            a0, a1 = (x, x + w) if hor else (y, y + h)
            if min(hi, a1) - max(lo, a0) < 20.0:
                continue
            b0, b1 = (y, y + h) if hor else (x, x + w)
            if 0 <= c - b1 < clr:
                below = True
            if 0 <= b0 - c < clr:
                above = True
        if below and above:
            return True
    return False


TREE_FACE = {('sp_gather', 'W'): 'W', ('sp_gather', 'E'): 'E', ('sp_pq', 'W'): 'W', ('sp_pq', 'E'): 'E'}


def tree_rows(R, trees, ports, hub_x):
    rows = []
    mid = (hub_x[0] + hub_x[1]) / 2
    for root, fr, w in trees:
        pts = [(ports[k], v) for k, v in fr.items() if k in ports]
        if not pts or root not in R:
            continue
        side = 'W' if sum(p[0][0] for p in pts) / len(pts) < mid else 'E'
        rb = ns(root, R[root])
        face = TREE_FACE.get((root, side), side)
        cy = sorted(p[0][1] for p in pts)[len(pts) // 2]
        rp = HR.face_point(rb, face, None, SimpleNamespace(x=rb.x, y=cy, w=0, h=0))
        d = [abs(p[0] - rp[0]) + abs(p[1] - rp[1]) for p, _ in pts]
        bm = sum(v * di for (_, v), di in zip(pts, d)) / 1000
        rows.append(dict(root=root, side=side, leaves=len(pts), width=w, worst_um=round(max(d), 1),
                         worst_stages=stages(max(d)), mean_um=round(sum(d) / len(d), 1), bit_mm=round(bm, 1),
                         root_point=[round(rp[0], 1), round(rp[1], 1)], entry_y=round(cy, 1)))
    return rows


# ------------------------------------------------------------------ congestion (negotiated gcell maze route)
def grid(hub_x):
    x0 = hub_x[0] - 600.0
    nx = int(math.ceil((hub_x[1] + 600.0 - x0) / G))
    ny = int(math.ceil(26000.0 / G))
    return x0, nx, ny


def cell(x, y, gr):
    x0, nx, ny = gr
    return min(nx - 1, max(0, int((x - x0) / G))), min(ny - 1, max(0, int(y / G)))


def blocked(R, gr):
    blk = set()
    for k, (x, y, w, h) in list(R.items()) + [(HCP_ROW[0], HCP_ROW[1:])]:
        if k == 'pq_cnt':
            continue
        i0, j0 = cell(x + G / 2, y + G / 2, gr)
        i1, j1 = cell(x + w - G / 2, y + h - G / 2, gr)
        for i in range(i0, i1 + 1):
            for j in range(j0, j1 + 1):
                blk.add((i, j))
    return blk


def free_near(c, blk, gr, d):
    for _ in range(60):
        if c not in blk:
            return c
        c = (min(gr[1] - 1, max(0, c[0] + d[0])), min(gr[2] - 1, max(0, c[1] + d[1])))
    return c


def astar(s, t, gr, blk, use, bits):
    _, nx, ny = gr

    def h(c):
        return abs(c[0] - t[0]) + abs(c[1] - t[1])
    dist = {s: 0.0}
    prev = {}
    pq = [(h(s), 0.0, s)]
    while pq:
        _, d, c = heapq.heappop(pq)
        if c == t:
            break
        if d > dist.get(c, 1e18):
            continue
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (c[0] + dx, c[1] + dy)
            if not (0 <= n[0] < nx and 0 <= n[1] < ny) or (n in blk and n != t):
                continue
            e = (min(c[0], n[0]), min(c[1], n[1]), 'h' if dx else 'v')
            u = (use.get(e, 0.0) + bits) / (CAP_H if dx else CAP_V)
            nd = d + 1.0 + (0 if u < 0.5 else 4 * (u - 0.5)) + (0 if u < 1.0 else 50 * (u - 1.0))
            if nd < dist.get(n, 1e18):
                dist[n] = nd
                prev[n] = (c, e)
                heapq.heappush(pq, (nd + h(n), nd, n))
    path = []
    c = t
    while c != s and c in prev:
        c, e = prev[c]
        path.append(e)
    return path


def spread(R, a, f, n, other):
    x, y, w, h = R[a]
    o = R[other]
    if f in 'NS':
        lo, hi = max(x, o[0]), min(x + w, o[0] + o[2])
        if hi - lo < 50.0:
            lo, hi = x, x + w
        return [((lo + (hi - lo) * (k + .5) / n), y + h + G / 2 if f == 'N' else y - G / 2) for k in range(n)]
    lo, hi = max(y, o[1]), min(y + h, o[1] + o[3])
    if hi - lo < 50.0:
        lo, hi = y, y + h
    return [(x + w + G / 2 if f == 'E' else x - G / 2, lo + (hi - lo) * (k + .5) / n) for k in range(n)]


def congestion(R, p2p_r, tree_r, hub_x, channels):
    gr = grid(hub_x)
    blk = blocked(R, gr)
    nets = []
    D = dict(N=(0, 1), S=(0, -1), E=(1, 0), W=(-1, 0))
    for r in p2p_r:
        if r['len_um'] <= G:
            continue                          # abutting pin-to-pin: no gcell route
        nb = max(1, math.ceil(r['bits'] / BUNDLE))
        sa = spread(R, r['a'], r['faces'][0], nb, r['b'])
        sb = spread(R, r['b'], r['faces'][1], nb, r['a'])
        for k in range(nb):
            ca = free_near(cell(*sa[k], gr), blk, gr, D[r['faces'][0]])
            cb = free_near(cell(*sb[k], gr), blk, gr, D[r['faces'][1]])
            nets.append((r['bits'] / nb, ca, cb))
    for ti, t in enumerate(tree_r):
        road = channels.get('S14W' if t['side'] == 'W' else 'S14E')
        nb = max(1, math.ceil(t['width'] / BUNDLE))
        f = TREE_FACE.get((t['root'], t['side']), t['side'])
        sb = spread(R, t['root'], f, nb, t['root'])
        for k in range(nb):
            # trunks spread over their S14 road width (one lane per bundle, trees interleaved)
            fr = ((ti * 0.37 + (k + 0.5) / nb) % 1.0)
            x = (road[0] + 100.0 + (road[2] - road[0] - 200.0) * fr) if road else \
                (hub_x[0] + 200.0 if t['side'] == 'W' else hub_x[1] - 200.0)
            # the trunk climbs in its S14 road (field side) and enters the hub at the root's height (canonical roads)
            nets.append((t['width'] / nb, cell(x, sb[k][1], gr), free_near(cell(*sb[k], gr), blk, gr, D[f])))
            nets.append((t['width'] / nb, cell(x, t['entry_y'], gr), cell(x, sb[k][1], gr)))
    nets.sort(key=lambda n: -abs(n[1][0] - n[2][0]) - abs(n[1][1] - n[2][1]))
    use = {}
    for it in range(2):
        if it:
            use = {}
        for bits, s, t in nets:
            for e in astar(s, t, gr, blk, use, bits):
                use[e] = use.get(e, 0.0) + bits
    util = {e: v / (CAP_H if e[2] == 'h' else CAP_V) for e, v in use.items()}
    out = dict(max_util=round(max(util.values()), 3), edges_over_060=sum(u > 0.60 for u in util.values()),
               edges_over_100=sum(u > 1.0 for u in util.values()))
    x0 = gr[0]
    per = {}
    for name, (cx0, cy0, cx1, cy1) in channels.items():
        us = [u for (i, j, _), u in util.items() if cx0 <= x0 + (i + .5) * G <= cx1 and cy0 <= (j + .5) * G <= cy1]
        per[name] = round(max(us), 3) if us else 0.0
    out['channels'] = per
    return out, util, gr


def channels_of(L, R):
    if L is None:
        return {}
    w = L['wide']
    out = dict(S14W=(w['s14w'][0], 0, w['s14w'][1], 26000), S14E=(w['s14e'][0], 0, w['s14e'][1], 26000))
    vm, su = R.get('sp_vm'), R.get('sp_su_s')
    if vm and su and su[1] + su[3] <= vm[1]:
        out['SU|VM'] = (vm[0], su[1] + su[3], vm[0] + vm[2], vm[1])
    hs = R.get('sp_hc_s')
    if hs and vm:
        out['VM|HC'] = (vm[0] + vm[2], vm[1], hs[0], vm[1] + vm[3]) if hs[0] > vm[0] + vm[2] else \
            (vm[0] + vm[2], vm[1], hs[0], vm[1] + vm[3])
    c = L.get('corridor')
    if c:
        out['HC corridor'] = (c[0], c[1], c[0] + c[2], c[1] + c[3])
    return out


def evaluate(model_rects, p2p, trees, ports, L, hub_x):
    R = layout_rects(model_rects, L)
    pr = p2p_rows(R, p2p, band_faces(L))
    tr = tree_rows(R, trees, ports, hub_x)
    cong, util, gr = congestion(R, pr, tr, hub_x, channels_of(L, R))
    return R, pr, tr, cong, util, gr


def render(R, util, gr, png, title, rows):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    x0, nx, ny = gr
    m = np.zeros((ny, nx))
    for (i, j, _), u in util.items():
        m[j, i] = max(m[j, i], u)
    fig, ax = plt.subplots(figsize=(7.5, 12))
    ext = [x0 / 1e3, (x0 + nx * G) / 1e3, 0, ny * G / 1e3]
    im = ax.imshow(np.ma.masked_where(m == 0, m), origin='lower', extent=ext, cmap='turbo', vmin=0, vmax=1.0,
                   interpolation='nearest')
    for k, (x, y, w, h) in R.items():
        if x + w < x0 or x > x0 + nx * G:
            continue
        ax.add_patch(plt.Rectangle((x / 1e3, y / 1e3), w / 1e3, h / 1e3, fill=True, fc='#d9d9d9', ec='k', lw=0.6, alpha=0.85))
        ax.text((x + w / 2) / 1e3, (y + h / 2) / 1e3, k.replace('sp_', ''), ha='center', va='center', fontsize=6)
    for r in rows[:14]:
        p = np.array(r['path']) / 1e3
        ax.plot(p[:, 0], p[:, 1], lw=0.5 + 2.5 * min(1.0, r['bits'] / 17000), color='#c0392b', alpha=0.7)
    ax.set_xlim(ext[0], ext[1])
    ax.set_ylim(0, 26)
    ax.set_title(title, fontsize=8)
    ax.set_xlabel('x (mm)')
    ax.set_ylabel('y (mm)')
    fig.colorbar(im, ax=ax, fraction=0.04, label='gcell-edge utilisation (bits/um / tracks/um)')
    fig.tight_layout()
    fig.savefig(png, dpi=110)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--model', required=True, type=Path)
    ap.add_argument('--layout', action='append', required=True, help='NAME=hub_layout.json')
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--png-dir', type=Path)
    a = ap.parse_args()
    model = load(a.model)
    p2p, trees, ports, mrects = flows_of(model)
    res = {}
    for spec in a.layout:
        name, path = spec.split('=', 1)
        L = load(path)
        hub_x = L['checks']['hub_um']
        R, pr, tr, cong, util, gr = evaluate(mrects, p2p, trees, ports, L, hub_x)
        big = [r for r in pr if r['bits'] >= 500]
        res[name] = dict(layout=path, p2p=pr, trees=tr, congestion=cong,
                         totals=dict(p2p_bit_mm=round(sum(r['bit_mm'] for r in pr)),
                                     tree_bit_mm=round(sum(r['bit_mm'] for r in tr)),
                                     big_pair_stages=sum(r['stages'] for r in big),
                                     big_pair_bit_stages=sum(r['stages'] * r['bits'] for r in big),
                                     worst_tree_stages=max(r['worst_stages'] for r in tr)))
        if a.png_dir:
            a.png_dir.mkdir(parents=True, exist_ok=True)
            render(R, util, gr, a.png_dir / f'screen_{name}.png',
                   f"{name}: max gcell util {cong['max_util']}, >0.60 {cong['edges_over_060']}", pr)
        print(name, json.dumps(res[name]['totals']), json.dumps(cong))
    names = list(res)
    keys = sorted({(r['a'], r['b']) for n in names for r in res[n]['p2p']}, key=lambda k: -max(
        r['bits'] for n in names for r in res[n]['p2p'] if (r['a'], r['b']) == k))
    print('%-36s %6s ' % ('pair', 'bits') + ' '.join('%14s' % n for n in names))
    for k in keys:
        rr = [next((r for r in res[n]['p2p'] if (r['a'], r['b']) == k), None) for n in names]
        print('%-36s %6d ' % ('-'.join(k), max(r['bits'] for r in rr if r)) +
              ' '.join('%7.0f um %2d st' % (r['len_um'], r['stages']) if r else '%14s' % '-' for r in rr))
    for n in names:
        for t in res[n]['trees']:
            print(n, t['root'], t['side'], t['leaves'], 'worst', t['worst_um'], t['worst_stages'], 'bit_mm', t['bit_mm'])
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(dict(schema='opentallas.s81.hub_compact_screen.v1', scope='PLANNING SCREEN (not GEN/GRT)',
                                     model=str(a.model), hop_um=HOP, gcell_um=G, results=res), indent=1) + '\n')


if __name__ == '__main__':
    main()
