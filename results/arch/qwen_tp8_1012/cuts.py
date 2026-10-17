#!/usr/bin/env python3
"""Cut analysis inputs for the TP8 SPEC (qwen-tp8/spec, 2026-10-12): bits crossing cut lines vs usable ASAP7 tracks,
measured on the die generators' bus networks (relay-staged, pins projected onto the face toward the peer).

  dump:  python3 cuts.py dump OUT_DIR   (run from a tree whose tools/die_top_lint.py has the recipe: tp8a lives on
         claude/el1011-qwen-tp8-die a13e30ceb; r22ko4 and the KV die (closed flags) are on main) -> OUT_DIR/{rom_tp8a,r22ko4,kv}.json
  scan:  python3 cuts.py scan OUT_DIR   -> cuts.json next to this file (read by gen.py)

Capacity rule (as results/arch/hbm_die_phy_study_1012/cuts.py): ASAP7 pitches M4/M5 48 nm, M6/M7 64 nm, M8/M9 80 nm.
A vertical cut is crossed by horizontal layers.  Over a hard block (> 0.04 mm2) only the die layer counts (M8 for a
vertical cut, M9 for a horizontal one) at 75 % after the PDN; in channels add M6/M7 at 75 % and M4/M5 at 50 %.
Two window sizes: COARSE (tile row / column pitch / spine / IO band) and FINE (260 um, half a row gap: the size at which
stacked words overflow GRT).  Calibration: r22ko4 (die GRT overflow 155k on M6/M8 H) peaks at 1.05 on the fine H scan
(tree-root words stacked in one row), the closed KV die (GRT overflow 0) at 0.87 (one block-local bundle)."""
import json, sys, collections
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
TPU = {'M4': 1 / 0.048, 'M5': 1 / 0.048, 'M6': 1 / 0.064, 'M7': 1 / 0.064, 'M8': 1 / 0.080, 'M9': 1 / 0.080}
FINE = 260.0
# contract v3 (qwen-tp8/die 2026-10-12, owner layer study): die slots are capped at M5 (signals + PG), so over an M5-capped
# block the die also owns M6 / M7 (75 % after the die PDN).  CAP_MODE 'asbuilt' keeps the old rule (die layer only over
# every block); 'v3' applies the cap to every block whose master is not hard IP (HBM PHY, SerDes, UCIe, PLL, clock rx).
CAP_MODE = 'asbuilt'
HARD_IP = ('ot_hbm3e_phy', 'qfd_io_serdes', 'qfd_io_ucie', 'qkd_pll', 'qfd_clkrx')
# coordinator DECISION 2026-10-12 12:15: qfd_tile_nk / h3c / h3s is a CLUSTER slot (hard ROM/SRAM/leaf children, M2-M7,
# PG M7): the die routes over it on M8+ only, so for the die cut model it counts like hard IP (die layer only).
CLUSTER = ('qfd_tile_nk', 'qfd_tile_nl', 'qfd_tile_h3c', 'qfd_tile_h3s')
# layer plan B (coordinator 2026-10-12 relaxation, evaluated): tile_nk capped at M6 (leaves M5 incl. PG; tile PG strap
# + horizontal ROM-band crossing on M6) -> the die owns M7 + M8 (+M9) over the cluster.  CLUSTER_PLAN 'B' adds M7 (75 %)
# to vertical-wire (horizontal-cut) capacity over CLUSTER blocks; horizontal wires still see M8 only (M6 is the tile's).
CLUSTER_PLAN = 'A'
# coordinator DECISION 2026-10-13 (tile growth, die lead r8): the qfd_tile_nk slot is M5-capped (signals + PG), so the
# die owns M6 over the tile field for HORIZONTAL buses.  CLUSTER_PLAN 'M6' adds M6 (75 % after the die PDN) to the
# horizontal-wire (vertical-cut) capacity over CLUSTER blocks; vertical wires over a tile stay on M9 only (M7 is not
# counted: the decision names M6 only).  Relay sites stay in the row gaps / column corridors.


def dump(out):
    sys.path.insert(0, 'tools')
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    import die_top_lint as D
    from qwen_kv_die import kv_die as KV
    def wr(m, name):
        ins = [dict(n=i.name, m=getattr(i, 'master', ''), x=i.x, y=i.y, w=i.w, h=i.h) for i in m['insts']]
        json.dump(dict(insts=ins, buses=[(b, c, bits, [e[0] for e in eps]) for b, c, bits, eps in m['buses']]), open(out / name, 'w'))
    wr(KV.build(kv_wq_leaves=True, kv_wq_binary=True, kv_wq_leaf_s=True, kv_wq_wide=True, kv_wq_mirror=True), 'kv.json')
    for rec, name in (('tp8b', 'rom_tp8b.json'), ('tp8a', 'rom_tp8a.json'), ('r22ko4', 'r22ko4.json')):
        if rec not in D.QWEN_RECIPES:
            continue
        D.QWEN_RECIPE = rec; D._QW.clear(); D.QSRC = None
        wr(D.load_qwen()[1], name)


def block_model(insts):
    """(blocks, cap5, clB) of an instance list (dicts with x/y/w/h/m) under the current CAP_MODE / CLUSTER_PLAN: the
    capacity side of the cut model, shared with the die generator's field allocator (qwen-tp8/die it24: its per-window
    caps are usable(...) x ~0.58, not a flat number)."""
    bl = [i for i in insts if i['w'] * i['h'] > 4e4]
    return (np.array([(i['x'], i['y'], i['x'] + i['w'], i['y'] + i['h']) for i in bl]).reshape(-1, 4),
            np.array([CAP_MODE == 'v3' and i.get('m', '') not in HARD_IP + CLUSTER for i in bl], dtype=bool),
            np.array([({'B': 1, 'M6': 2}.get(CLUSTER_PLAN, 0) if i.get('m', '') in CLUSTER else 0) for i in bl], dtype=int))


def usable(ax, cp, edges, blocks, cap5, clB):
    """usable tracks per window (edges along the cut line ax = cp) and the hard-block coverage per window."""
    p0, o0 = (0, 1) if ax == 'x' else (1, 0)
    sel = (blocks[:, p0] < cp) & (cp < blocks[:, p0 + 2])
    B = blocks[sel]
    # plan B: die M7 over the cluster serves vertical wires only; plan M6: die M6 over it serves horizontal wires only
    K5 = cap5[sel] | ((clB[sel] == 1) & (ax == 'y')) | ((clB[sel] == 2) & (ax == 'x'))
    cov = np.zeros(len(edges) - 1); cov5 = np.zeros(len(edges) - 1)
    for b, k5 in zip(B, K5):
        o = np.clip(np.minimum(edges[1:], b[o0 + 2]) - np.maximum(edges[:-1], b[o0]), 0, None)
        cov += o
        if k5: cov5 += o
    L = np.diff(edges); cov = np.minimum(cov, L); cov5 = np.minimum(cov5, cov)
    hi, lo, lw = ('M8', 'M6', 'M4') if ax == 'x' else ('M9', 'M7', 'M5')
    return 0.75 * L * TPU[hi] + cov5 * 0.75 * TPU[lo] + (L - cov) * (0.75 * TPU[lo] + 0.5 * TPU[lw]), cov


class Net:
    def __init__(self, path, drop=('clock_trunk',)):
        d = json.load(open(path)); self.I = I = {i['n']: i for i in d['insts']}
        self.blocks, self.cap5, self.clB = block_model(d['insts'])
        self.W = max(i['x'] + i['w'] for i in d['insts']); self.H = max(i['y'] + i['h'] for i in d['insts'])
        cen = lambda i: (i['x'] + i['w'] / 2, i['y'] + i['h'] / 2)
        cl = lambda i, P: (min(max(P[0], i['x']), i['x'] + i['w']), min(max(P[1], i['y']), i['y'] + i['h']))
        seg, cls = [], []
        for b, c, bits, eps in d['buses']:
            p = [I[e] for e in eps if e in I]
            if len(p) < 2 or c in drop: continue      # clock nets are one tree each, built by CTS in the spine channel
            for a, q in (list(zip(p, p[1:])) if len(p) == 2 else [(p[0], t) for t in p[1:]]):
                A, Q = cl(a, cen(q)), cl(q, cen(a))   # pin on the face toward the peer
                # die lead r9 (2026-10-13): two ABUTTED blocks (gap <= 1 um) exchange the bus face to face over the
                # shared edge: no die wire.  The centre projection drew a jog along the seam when one block is much
                # wider than the other (SU 778 um on the 4,709-um VM N face: 8,511 b 'crossing' 388 um of x cuts)
                ox = min(a['x'] + a['w'], q['x'] + q['w']) - max(a['x'], q['x'])
                oy = min(a['y'] + a['h'], q['y'] + q['h']) - max(a['y'], q['y'])
                if (ox > 0 and -1.0 <= -oy <= 1.0) or (oy > 0 and -1.0 <= -ox <= 1.0):
                    continue
                seg.append((A[0], A[1], Q[0], Q[1], bits)); cls.append(c)
        self.S = np.array(seg); self.C = np.array(cls)

    def cut(self, ax, cp, edges):
        """bits per window (edges along the cut), usable tracks per window, family split per window."""
        p0, p1, o0, o1 = (0, 2, 1, 3) if ax == 'x' else (1, 3, 0, 2)
        S = self.S; m = (np.minimum(S[:, p0], S[:, p1]) < cp) & (cp < np.maximum(S[:, p0], S[:, p1]))
        T = S[m]; C = self.C[m]
        oc = T[:, o0] + (T[:, o1] - T[:, o0]) * (cp - T[:, p0]) / (T[:, p1] - T[:, p0])
        k = np.digitize(oc, edges) - 1
        bits = np.bincount(np.clip(k, 0, len(edges) - 2), weights=T[:, 4] * ((k >= 0) & (k < len(edges) - 1)), minlength=len(edges) - 1)
        cap, cov = usable(ax, cp, edges, self.blocks, self.cap5, self.clB)
        return bits, cap, cov, k, C, T[:, 4]

    def window(self, ax, cp, lo, hi):
        bits, cap, cov, k, C, w = self.cut(ax, cp, np.array([lo, hi]))
        fam = collections.Counter()
        for c, b, kk in zip(C, w, k):
            if kk == 0: fam[c] += int(b)
        return dict(ax=ax, pos=round(cp), win=[round(lo), round(hi)], bits=int(bits[0]), block_um=round(cov[0]),
                    usable=round(cap[0]), util=round(bits[0] / cap[0], 3), fam=dict(fam.most_common(5)))

    def fine(self, top=8, step=50.0):
        res = []
        for ax, span, other in (('x', self.W, self.H), ('y', self.H, self.W)):
            edges = np.arange(0, other + FINE, FINE)
            for cp in np.arange(step, span, step):
                bits, cap, cov, k, C, w = self.cut(ax, cp, edges)
                u = bits / cap
                for j in np.argsort(-u)[:2]:
                    if bits[j] > 0: res.append((float(u[j]), ax, float(cp), float(edges[j])))
        res.sort(reverse=True); out = []
        for u, ax, cp, w0 in res:
            if any(ax == o['ax'] and abs(cp - o['pos']) < 400 and abs(w0 - o['win'][0]) < 600 for o in out): continue
            out.append(self.window(ax, cp, w0, w0 + FINE))
            if len(out) >= top: break
        return out


def scan(md):
    md = Path(md); R = {}
    R['tp8a'] = rom_cuts(Net(md / 'rom_tp8a.json'))
    if (md / 'rom_tp8b.json').exists():
        B = Net(md / 'rom_tp8b.json')
        R['tp8b'] = rom_cuts(B)
        kvx = sorted({round(i['x'] + i['w']) for i in B.I.values() if i['n'] == 'land_WS'} | {round(i['x']) for i in B.I.values() if i['n'] == 'land_ES'})
        R['tp8b']['kv_strip_x_max'] = max((B.window('x', x, y, y + 1486) for x in (3650, B.W - 3650) for y in range(0, int(B.H) - 1486, 200)), key=lambda r: r['util'])
    K = Net(md / 'kv.json')
    R['kv_die'] = dict(die=[round(K.W), round(K.H)], half_boundary_x=dict(W=3700, E=4650),
                       W_rows_1496=[int(b) for b in K.cut('x', 3700, np.arange(0, K.H + 1496, 1496))[0]],
                       E_rows_1496=[int(b) for b in K.cut('x', 4650, np.arange(0, K.H + 1496, 1496))[0]],
                       centre_col_V_max=max((K.window('y', y, 3700, 4650) for y in range(300, 24400, 200)), key=lambda r: r['util']),
                       half_V_max=max((K.window('y', y, 0, 3700) for y in range(300, 24400, 200)), key=lambda r: r['util']),
                       centre_x_full=K.window('x', 4175, 0, K.H), fine=K.fine())
    Rk = Net(md / 'r22ko4.json')
    R['r22ko4_calibration'] = dict(grt_overflow='155k (M6/M8 H), r22ko4 e6/e7 die chains', fine=Rk.fine(top=4))
    R['kv_die']['grt'] = 'overflow 0, TT +88.90 / FF +17.51 (KV die, contract qwen_kv v5)'
    json.dump(R, open(HERE / 'cuts.json', 'w'), indent=1)
    print(json.dumps({k: (v.get('row_H_max'), v.get('fine', [None])[0]) if isinstance(v, dict) else v for k, v in R.items()}, default=str)[:3000])


def rom_cuts(A):
    """Coarse row / spine / column / IO-band windows + the fine scan on a ROM-family die (tp8a, tp8b)."""
    t = sorted((i for i in A.I.values() if i['m'] == 'qfd_tile_nk'), key=lambda i: (i['y'], i['x']))
    rows = sorted({round(i['y'], 1) for i in t}); cols = sorted({round(i['x'], 1) for i in t}); th, tw = t[0]['h'], t[0]['w']
    j = max(range(len(cols) - 1), key=lambda k: cols[k + 1] - cols[k])     # the spine: the widest gap between columns
    sp = (cols[j] + tw, cols[j + 1])
    gap = rows[1] - rows[0] - th
    rr = []
    for y in rows:
        best = max((A.window('x', x, y - gap / 2, y + th + gap / 2) for x in [c + f for c in cols for f in (tw / 2, tw + 26)] + [sp[0] + 5, sp[1] - 5]),
                   key=lambda r: r['util'])
        rr.append(best)
    return dict(geometry=dict(rows=len(rows), cols=len(cols), tile=[round(tw, 2), round(th, 2)], row_pitch=round(rows[1] - rows[0], 1),
                                   col_pitch=round(cols[1] - cols[0], 2), spine_x=[round(sp[0]), round(sp[1])], die=[round(A.W), round(A.H)]),
                     row_H=rr, row_H_max=max(rr, key=lambda r: r['util']),
                     spine_V_max=max((A.window('y', y, *sp) for y in range(int(rows[0]), int(rows[-1] + th), 200)), key=lambda r: r['util']),
                     col_V_max=max((A.window('y', (rows[k] + th + rows[k + 1]) / 2, c - 26, c + tw + 26) for k in range(len(rows) - 1) for c in cols), key=lambda r: r['util']),
                     io_band=A.window('y', rows[-1] + th + 1, 0, A.W), io_band_S=A.window('y', rows[0] - 1, 0, A.W),
                     fine=A.fine(), fine_tree=Net.fine(_sub(A, ('io', 'crom'))))


def _sub(n, drop):
    m = ~np.isin(n.C, drop); s = object.__new__(Net); s.__dict__.update(n.__dict__); s.S = n.S[m]; s.C = n.C[m]; return s


if __name__ == '__main__':
    {'dump': dump, 'scan': scan}[sys.argv[1]](sys.argv[2])
