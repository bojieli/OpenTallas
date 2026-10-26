#!/usr/bin/env python3
"""QC-SU-LAT-R3 (METHODOLOGY 12.8b/c/d1 + 12.2a1): plan-computed INTERNAL H-TREE for one hard-core type.

  entry (slice clock pin, M5 interior)  -> root BUFx24 [+ designed entry chain, fixed]      (entry island, pushdown, FIRM)
  -> 4 equal-stage legs, one mid repeater each (M level)                                    (placed, dont_touch)
  -> 4 LEAF ISLANDS on the 4 equal-load sink clusters, BUFx24 driver each (Q level)         (pushdown, FIRM, plan coords)
  -> 4 branch nodes per island (B) -> 4 sub nodes per branch (S) -> 2^k leaf drivers per sub (<= TAPMAX sinks each)
  -> register clock pins.  Macro (SRAM) clock pins: ONE designed leaf stage on the S net nearest the macro CK pin
     = same depth / same cell as the register leaves (no pad cells).  TritonCTS is not run (OT_H_NO_TRITON=1):
     every buffer of the tree is placed by this plan; nothing is sized after a measurement.

Equal load by construction: every level is a median bisection of the sink set (2 cuts per fanout-4 level), so all groups at
a level hold the same sink count (+-1) and the leaf regions tile the core (rect assignment in the build).

Usage: mkspec_h.py GEO SLICE.json TYPE OUT_SPEC OUT_JSON [--tapmax 24] [--islands x,y;x,y;x,y;x,y] [--entry-n N|model]
GEO = geo_dump.tcl output (CORE/MACRO/SINK lines) of the type's GEOM-reviewed placement.
"""
import sys, math, json, argparse

ap = argparse.ArgumentParser()
ap.add_argument('geo'); ap.add_argument('slice'); ap.add_argument('type'); ap.add_argument('out'); ap.add_argument('outjson')
ap.add_argument('--tapmax', type=int, default=24)
ap.add_argument('--islands', default='', help='fixed island centres "x,y;x,y;x,y;x,y" (slice); default = equal-load cluster centroids')
ap.add_argument('--entry-n', default='model')
ap.add_argument('--target', type=float, default=250.0)
ap.add_argument('--group', default='sector', choices=['sector', 'nearest'])
a = ap.parse_args()

S = json.load(open(a.slice)); isl = {i['name']: i for i in S['islands']}
ex, ey = isl['clock_entry']['clock_pin']['xy_um']; er = isl['clock_entry']['rect_um']
LAT = 4.32; HALO = 4.32
sinks, macros = [], []
for ln in open(a.geo):
    f = ln.split()
    if not f: continue
    if f[0] == 'CORE': cx0, cy0, cx1, cy1 = map(float, f[1:5])
    elif f[0] == 'MACRO': macros.append((f[1], tuple(map(float, f[3:7])), (float(f[8]), float(f[9]))))
    elif f[0] == 'SINK': sinks.append((float(f[1]), float(f[2])))
blk = [(p - HALO, q - HALO, r + HALO, s + HALO) for _, (p, q, r, s), _ in macros]
eblk = (er[0] - 0.5, er[1] - 0.5, er[2] + 0.5, er[3] + 0.5)

def free(p, m=0.6, entry_ok=False):
    x, y = p
    if not (cx0 + 1.5 <= x <= cx1 - 3 and cy0 + 1 <= y <= cy1 - 1): return False
    if any(b0 - m < x < b2 + m and b1 - m < y < b3 + m for b0, b1, b2, b3 in blk): return False
    if not entry_ok and eblk[0] < x < eblk[2] and eblk[1] < y < eblk[3]: return False
    return True

def snap(p, step=0.5):
    if free(p): return p
    for r in [i * step for i in range(1, 1200)]:
        for dx, dy in [(r, 0), (-r, 0), (0, r), (0, -r), (r, r), (-r, -r), (r, -r), (-r, r)]:
            q = (p[0] + dx, p[1] + dy)
            if free(q): return q
    raise SystemExit('no free point near %s' % (p,))

def snap_lat(p):
    """island centre: nearest 4.32-lattice point whose whole 8.64 island rect is free (outside macro halos)"""
    gx, gy = round(p[0] / LAT) * LAT, round(p[1] / LAT) * LAT
    best = None
    for i in range(-30, 31):
        for j in range(-30, 31):
            q = (gx + i * LAT, gy + j * LAT)
            if all(free((q[0] + dx, q[1] + dy), m=0.0) for dx in (-4.32, 0, 4.32) for dy in (-4.32, 0, 4.32)):
                d = abs(q[0] - p[0]) + abs(q[1] - p[1])
                if best is None or d < best[0]: best = (d, q)
    if best is None: raise SystemExit('no free lattice island near %s' % (p,))
    return (round(best[1][0], 3), round(best[1][1], 3))

d1 = lambda p, q: abs(p[0] - q[0]) + abs(p[1] - q[1])
cen = lambda P: (sum(p[0] for p in P) / len(P), sum(p[1] for p in P) / len(P))

def bisect(P, rect):
    x0, y0, x1, y1 = rect
    sx = max(p[0] for p in P) - min(p[0] for p in P); sy = max(p[1] for p in P) - min(p[1] for p in P)
    ax = 0 if sx >= sy else 1
    P = sorted(P, key=lambda p: (p[ax], p[1 - ax])); h = len(P) // 2; cut = (P[h - 1][ax] + P[h][ax]) / 2
    r1, r2 = ((x0, y0, cut, y1), (cut, y0, x1, y1)) if ax == 0 else ((x0, y0, x1, cut), (x0, cut, x1, y1))
    return [(P[:h], r1), (P[h:], r2)]

def split(P, rect, cuts):
    out = [(P, rect)]
    for _ in range(cuts): out = [g for P_, r_ in out for g in bisect(P_, r_)]
    return out

ang = lambda p: math.atan2(p[1] - ey, p[0] - ex)
def chunks(P, n, key):
    P = sorted(P, key=key); m = len(P)
    return [P[i * m // n:(i + 1) * m // n] for i in range(n)]
def sectors(P, n):
    """equal-load angular sectors about the entry; start angle = the largest angular gap (ring cut there)"""
    A = sorted(ang(p) for p in P); gaps = [(A[(i + 1) % len(A)] - A[i]) % (2 * math.pi) for i in range(len(A))]
    i0 = max(range(len(A)), key=lambda i: gaps[i]); a0 = A[(i0 + 1) % len(A)]
    return chunks(P, n, lambda p: (ang(p) - a0) % (2 * math.pi))
def medoid(P):
    c = cen(P); return min(P, key=lambda p: d1(p, c))

if a.group == 'sector':
    Qg = sectors(sinks, 4)
else:   # nearest slice island (load as the geometry gives it)
    fixed0 = [tuple(map(float, x.split(','))) for x in a.islands.split(';')]
    Qg = [[] for _ in fixed0]
    for p in sinks: Qg[min(range(len(fixed0)), key=lambda i: d1(p, fixed0[i]))].append(p)
nS = max(len(g) for g in Qg) / 16.0
k = max(0, math.ceil(math.log2(nS / a.tapmax / 1.0) - 1e-9)) if nS > a.tapmax else 0

# ---- island sites
if a.islands:
    fixed = [tuple(map(float, x.split(','))) for x in a.islands.split(';')]
    order = sorted([(d1(cen(g), f), gi, fi) for gi, g in enumerate(Qg) for fi, f in enumerate(fixed)])
    gq, used = {}, set()
    for d, gi, fi in order:
        if gi in gq or fi in used: continue
        gq[gi] = fixed[fi]; used.add(fi)
    qsites = [gq[i] for i in range(4)]
    src = 'slice'
else:
    qsites = [snap_lat(medoid(g)) for g in Qg]
    src = 'equal-load angular sector medoid, 4.32 lattice'

RC, RW = 'BUFx24_ASAP7_75t_R', 'BUFx16f_ASAP7_75t_R'
nodes, leaves, fixed_cells = [], [], []
R = (round(ex, 3), round(ey, 3))
def spatial(P, n):
    out = [P]
    while len(out) < n:
        nxt = []
        for G in out:
            sx = max(p[0] for p in G) - min(p[0] for p in G); sy = max(p[1] for p in G) - min(p[1] for p in G)
            nxt += chunks(G, 2, (lambda p: p[0]) if sx >= sy else (lambda p: p[1]))
        out = nxt
    return out
for qi, (P, qs) in enumerate(zip(Qg, qsites)):
    mid = snap(((ex + qs[0]) / 2, (ey + qs[1]) / 2))
    nodes.append(('M%d' % qi, 'root', mid, RW, len(P)))
    nodes.append(('Q%d' % qi, 'M%d' % qi, qs, RC, len(P)))
    fixed_cells.append(('ot_ms_Q%d_nd' % qi, RC, qs))
    # B / S: contiguous equal chunks along the ring (angle about the entry), then leaves by spatial bisection
    for bi, PB in enumerate(chunks(P, 4, ang) if a.group == 'sector' else spatial(P, 4)):
        bn = 'Q%dB%d' % (qi, bi); nodes.append((bn, 'Q%d' % qi, snap(cen(PB)), RW, len(PB)))
        for si, PS in enumerate(spatial(PB, 4)):
            sn = bn + 'S%d' % si; nodes.append((sn, bn, snap(cen(PS)), RW, len(PS)))
            for li, PL in enumerate(spatial(PS, 2 ** k)):
                leaves.append((sn + 'L%d' % li, sn, snap(cen(PL)), None, len(PL), PL))

mac = []
for nm, (p0, q0, p1, q1), ck in macros:
    site = snap((ck[0] - HALO - 1.2, ck[1]) if abs(ck[0] - p0) < abs(ck[0] - p1) else (ck[0] + HALO + 1.2, ck[1]))
    lf = min(leaves, key=lambda l: d1(l[2], site))
    mac.append((nm.replace('\\', '').replace('[', '*').replace(']', '*'), lf[0], site, ck))

# ---- plan model (12.9d predict-before-build): stage = d0 + Rd*C + Elmore(Lfar); wire star x 0.8 (Steiner), C 0.113 fF/um,
# r 0.0185 kohm/um (setRC_rcx M4/M5).  Cell constants: ASAP7 RVT TT NLDM at ~10-20 ps slew (lib, not a measurement).
CELL = {'BUFx24_ASAP7_75t_R': (17.5, 0.16, 2.9), 'BUFx16f_ASAP7_75t_R': (16.0, 0.22, 1.9), 'BUFx12f_ASAP7_75t_R': (16.0, 0.30, 1.4),
        'BUFx8_ASAP7_75t_R': (17.0, 0.45, 1.0), 'BUFx6f_ASAP7_75t_R': (17.0, 0.60, 0.8), 'BUFx4f_ASAP7_75t_R': (16.5, 0.90, 0.6)}
MENU = ['BUFx24_ASAP7_75t_R', 'BUFx16f_ASAP7_75t_R', 'BUFx12f_ASAP7_75t_R', 'BUFx8_ASAP7_75t_R', 'BUFx6f_ASAP7_75t_R', 'BUFx4f_ASAP7_75t_R']
CW, RWIRE, CDFF, CMAC = 0.113, 0.0185, 0.55, 4.0
pos = {'root': R}; par = {}; cell = {'root': RC}
for n, p, c, ce, _ in nodes: pos[n] = c; par[n] = p; cell[n] = ce
for n, p, c, _, _, _ in leaves: pos[n] = c; par[n] = p; cell[n] = RW
kids = {}
for n in par: kids.setdefault(par[n], []).append(n)
def stage(drv, loads_xy, cpins):
    d0, rd, _ = CELL[cell[drv]]
    if not loads_xy: return d0
    L = [d1(pos[drv], q) for q in loads_xy]
    cw = CW * 0.8 * sum(L)
    return d0 + rd * (cw + cpins) + 0.5 * RWIRE * CW * max(L) ** 2 + RWIRE * max(L) * cpins / max(1, len(L))
arr = {'root': 0.0}
def walk(n):
    ks = kids.get(n, [])
    if ks:
        mac_here = [m for m in mac if par.get(m[1]) == n]
        cp = sum(CELL[cell[c]][2] for c in ks) + CELL[RW][2] * len(mac_here)
        out = arr[n] + stage(n, [pos[c] for c in ks] + [m[2] for m in mac_here], cp)
        for c in ks: arr[c] = out + 0.5 * RWIRE * CW * d1(pos[n], pos[c]) ** 2 * 0.2
        for c in ks: walk(c)
walk('root')
def leaf_t(n, c, PL):
    d0, rd, _ = CELL[cell[n]]; L = [d1(c, q) for q in PL]; cw = CW * 0.6 * sum(L)
    return arr[n] + d0 + rd * (cw + CDFF * len(PL)) + 0.5 * RWIRE * CW * max(L) ** 2
def mac_t(m):
    d0, rd, _ = CELL[RW]; return arr[m[1]] + d0 + rd * (CW * d1(m[2], m[3]) + CMAC)
LEAFD = {n: (c, PL) for n, p, c, r, cnt, PL in leaves}
desc = {}
def dleaves(n):
    if n in LEAFD: return [n]
    if n not in desc: desc[n] = [x for k_ in kids.get(n, []) for x in dleaves(k_)]
    return desc[n]
def mean_arr(n):
    L = dleaves(n); return sum(leaf_t(x, *LEAFD[x]) for x in L) / len(L)
# d1 plan sizing, level by level (top-down): every node of a level gets the cell that brings its mean descendant
# leaf-register arrival closest to (not above) the level's slowest node with the strongest cell.  Weak cells only on
# short nets (max child distance < 40 um), else >= BUFx8.  Deterministic, from plan geometry; frozen with the spec.
levels = [['M%d' % i for i in range(4)], [n for n, *_ in nodes if len(n) == 4 and 'B' in n],
          [n for n, *_ in nodes if 'S' in n], [n for n, *_ in leaves]]
for lv in levels:
    for n in lv: cell[n] = MENU[0]
    walk('root'); tq = max(mean_arr(n) for n in lv)
    for n in lv:
        far = max([d1(pos[n], pos[c]) for c in kids.get(n, [])] + [d1(pos[n], q) for q in LEAFD.get(n, (None, []))[1]] + [0])
        menu = MENU if far < 40 else MENU[:4]
        best = None
        for ce in menu:
            cell[n] = ce; walk('root'); e = mean_arr(n) - tq
            if e <= 1.0 and (best is None or abs(e) < abs(best[0])): best = (e, ce)
        cell[n] = best[1]
    walk('root')
nodes = [(n, p, c, cell[n], cnt) for n, p, c, ce, cnt in nodes]
leafarr = [leaf_t(n, c, PL) for n, p, c, r, cnt, PL in leaves]
macarr = [mac_t(m) for m in mac]
pm = sum(leafarr) / len(leafarr)
ENTRY_D = CELL[RW][0] + CELL[RW][1] * (CELL[RW][2] + CW * 1.5)
if a.entry_n == 'model':
    en = max(0, int(round((a.target - pm) / ENTRY_D)))
else:
    en = int(a.entry_n)
for j in range(1, en + 1):
    fixed_cells.append(('ot_ms_entry%d' % j, RW, (round(ex - 2.6, 3), round(ey + 0.54 * (j - 3), 3))))  # column inside the 8.64 entry island
fixed_cells.insert(0, ('ot_ms_root', RC, (round(ex + 1.5, 3), round(ey, 3))))

o = ['# QC-SU-LAT-R3 internal H-tree (12.8b/c/d1, 12.2a1) GENERATED by mkspec_h.py %s for %s (slice %s, master_plan %s)'
     % (' '.join(sys.argv[1:3]), a.type, a.slice.split('/')[-1], S.get('master_plan_sha256', '')[:12]),
     '# entry (%.2f,%.2f) -> 4 legs (M) -> 4 leaf islands (Q, %s) %s -> B x4 -> S x4 -> leaves 2^%d; %d sinks, %d leaves (%d..%d sinks)'
     % (ex, ey, src, qsites, k, len(sinks), len(leaves), min(l[4] for l in leaves), max(l[4] for l in leaves)),
     '# plan model TT: leaf-register arrival mean %.1f min %.1f max %.1f, macro %.1f..%.1f; entry chain %d x BUFx16f (%.1f ps each) -> predicted mean %.1f'
     % (pm, min(leafarr), max(leafarr), min(macarr), max(macarr), en, ENTRY_D, pm + en * ENTRY_D),
     'set ot_ms_port ck', 'set ot_ms_root {%.3f %.3f}' % fixed_cells[0][2], 'set ot_h_entry_n %d' % en,
     'set ot_h_fixed {'] + [' {%s %s %.3f %.3f}' % (n, m, x, y) for n, m, (x, y) in fixed_cells] + ['}', 'set ot_ms_tree {']
o += [' {%s %s %.3f %.3f %s}' % (n, p, c[0], c[1], ce) for n, p, c, ce, _ in nodes] + ['}', 'set ot_ms_leaves {']
o += [' {%s %s {%.3f %.3f} {} %s}' % (n, p, c[0], c[1], cell[n]) for n, p, c, r, _, _ in leaves] + ['}', 'set ot_ms_macros {']
o += [' {%s %s {%.3f %.3f}}' % (x[0], x[1], x[2][0], x[2][1]) for x in mac] + ['}']
open(a.out, 'w').write('\n'.join(o) + '\n')
rep = {'type': a.type, 'slice': a.slice, 'master_plan_sha256': S.get('master_plan_sha256'), 'entry_pin': [ex, ey],
       'island_source': src, 'leaf_islands': [{'name': 'tree_leaf%d' % i, 'centre_um': list(q),
       'rect_um': [round(q[0] - 4.32, 3), round(q[1] - 4.32, 3), round(q[0] + 4.32, 3), round(q[1] + 4.32, 3)],
       'sinks': len(g), 'entry_to_island_um': round(d1((ex, ey), q), 2),
       'island_to_far_sink_um': round(max(d1(q, p) for p in g), 2), 'leg_cell': cell['M%d' % i]} for i, (g, q) in enumerate(zip(Qg, qsites))],
       'levels': {'M': 4, 'Q': 4, 'B': 16, 'S': 64, 'leaves': len(leaves), 'k': k, 'tapmax': a.tapmax},
       'model_TT': {'leaf_mean': round(pm, 1), 'leaf_min': round(min(leafarr), 1), 'leaf_max': round(max(leafarr), 1),
                    'Q_in': [round(arr['Q%d' % i], 1) for i in range(4)], 'macro_min': round(min(macarr), 1), 'macro_max': round(max(macarr), 1), 'entry_chain': en,
                    'entry_cell_ps': round(ENTRY_D, 1), 'pred_mean': round(pm + en * ENTRY_D, 1)},
       'fixed_cells': [[n, m, x, y] for n, m, (x, y) in fixed_cells]}
json.dump(rep, open(a.outjson, 'w'), indent=1)
print('\n'.join(o[:3]))
for i in rep['leaf_islands']: print('  ', i)
