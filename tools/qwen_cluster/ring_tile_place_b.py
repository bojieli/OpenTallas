#!/usr/bin/env python3
"""FAM-QK-CB16 10-21 (rgxb): ring_tile_place.py r0 model with the hard relay stations (qfd_c_stn514/516) FREE.

The r0 plan (stations fixed at the fullm bank positions) leaves 14 crossings whose writer / reader legs exceed 405 um: the
crossing sits between two stations spaced for a 3-hop soft bank.  Here every stn514/516 may move (43.2 lattice, own orientation
kept, window +-OT_RTPB_MOVE_UM around its fullm origin) together with the 69 ring tiles, so that
- every hard->hard hop (bank inputs hard_hops, incl. fixed ports / A0 / xstn) <= REACH,
- writer anchors -> ring tile in face and ring tile out face -> reader anchors <= REACH (anchors follow their station),
- soft ring->ring edges <= REACH,
- clearance: 21.6 um hard<->hard and ring<->hard, 10.8 um ring<->ring, 4.32 um around every scalar control / reset FF site.
No added cycles, no RTL change: only child origins move.  Objective: station displacement (x4) + ring displacement.
    ring_tile_place_b.py OUT.json [REACH_UM]
"""
import gzip, json, os, pathlib, sys
from ortools.sat.python import cp_model
ROOT = pathlib.Path(__file__).resolve().parents[2]
G = ROOT / 'results/arch/qw_cb16_legal_bays_1020/grid43'
d = json.load(gzip.open(G / 'qfd_c_b16_fullm_bank_inputs.json.gz'))
out_p = pathlib.Path(sys.argv[1]); REACH = float(sys.argv[2]) if len(sys.argv) > 2 else 405.0
U = 43200; R = round(REACH * 1000); TW, TH = 108000, 43200
MOVE = round(float(os.environ.get('OT_RTPB_MOVE_UM', 432)) * 1000)
EXCESS = round(float(os.environ.get('OT_RTPB_EXCESS_UM', 0)) * 1000)
# SQK-CB16C 10-21 (rgxc): port -> pin-register station legs are unregistered IO legs inside the 0.2 T IO budget (rgxb gate:
# 212-394 um legs, TT setup -583 ps at u_ft_0/d); OT_RTPB_IO_REACH_UM caps every FIX(port) <-> station hop separately.
R_IO = round(float(os.environ.get('OT_RTPB_IO_REACH_UM', REACH)) * 1000)
IO_CAP = {k: round(float(v) * 1000) for k, v in (e.split(':') for e in os.environ.get('OT_RTPB_IO_CAPS', '').split(',') if e)}   # per-station override
W, H = [round(x * 1000) for x in d['outline']]
nm = lambda v: round(v * 1000)
J = json.loads((G / 'qfd_c_b16_fullm_joint_solution.json').read_text())   # fulln child origins (= joint solution), not the bank-input ones
hard = {n: dict(h, X=nm(J['hard'][n][0]), Y=nm(J['hard'][n][1]), Wd=nm(h['width']), Ht=nm(h['height'])) for n, h in d['hard'].items()}
free = sorted(n for n, h in hard.items() if h['kind'] in ('qfd_c_stn514', 'qfd_c_stn516'))
rings = sorted({n[:-2] for n in d['halves']})
sites = []; old = {}
for l in (ROOT / 'physical/qcluster/qfd_c_b16_fullm_sites.tsv').read_text().splitlines():
    f = l.split('\t')
    if l.startswith('#'): continue
    if len(f) == 5:
        x, y, xlo, xhi = [nm(float(v)) for v in f[1:]]
        sites.append((xlo - 4320, y - 4320 - 1080, xhi + 4320, y + 4320 + 1080))
    elif len(f) == 7: old[f[0]] = [float(z) for z in f[1:]]
m = cp_model.CpModel()
P = {}                                     # node -> (Xexpr, Yexpr) in nm (int var or const)
for n, h in hard.items():
    if n in free:
        gx, gy = round(h['X'] / U), round(h['Y'] / U); k = MOVE // U
        top = 0 if (R_IO < R or IO_CAP) else 1         # rgxc: the face lattice row (>= 34.6 um margin) is legal for every station
        x = m.NewIntVar(max(min(1, gx), gx - k), min(max(gx, (W - h['Wd']) // U - top), gx + k), 'sx' + n)   # fullm origin always legal
        y = m.NewIntVar(max(min(1, gy), gy - k), min(max(gy, (H - h['Ht']) // U - top), gy + k), 'sy' + n)
        m.AddHint(x, gx); m.AddHint(y, gy); P[n] = (U * x, U * y, x, y)
    else:
        P[n] = (h['X'], h['Y'], None, None)
def box(n):                                # (x expr, y expr, w, h)
    return P[n][0], P[n][1], hard[n]['Wd'], hard[n]['Ht']
def sep(ax, ay, aw, ah, bx, by, bw, bh, gap):
    fl = [m.NewBoolVar('') for _ in range(4)]
    m.Add(ax + aw + gap <= bx).OnlyEnforceIf(fl[0]); m.Add(bx + bw + gap <= ax).OnlyEnforceIf(fl[1])
    m.Add(ay + ah + gap <= by).OnlyEnforceIf(fl[2]); m.Add(by + bh + gap <= ay).OnlyEnforceIf(fl[3]); m.AddBoolOr(fl)
def near(n, cx, cy, rad):                  # could node n (window incl.) come within rad of point
    h = hard[n]; mv = MOVE if n in free else 0
    return abs(h['X'] + h['Wd'] / 2 - cx) <= rad + mv + h['Wd'] / 2 and abs(h['Y'] + h['Ht'] / 2 - cy) <= rad + mv + h['Ht'] / 2
# hard <-> hard clearance 21.6 (pairs involving a free station, within reach of each other)
names = sorted(hard)
for i, a in enumerate(names):
    for b in names[i + 1:]:
        if a not in free and b not in free: continue
        ha, hb = hard[a], hard[b]
        lim = MOVE * 2 + 21600 + max(ha['Wd'], ha['Ht']) + max(hb['Wd'], hb['Ht'])
        if abs(ha['X'] - hb['X']) > lim or abs(ha['Y'] - hb['Y']) > lim: continue
        sep(*box(a), *box(b), 21600)
for n in free:                             # free station vs scalar sites (4.32 already in the site rect)
    h = hard[n]
    for (a, b, c, e) in sites:
        if not near(n, (a + c) / 2, (b + e) / 2, 60000 + (c - a) / 2): continue
        sep(*box(n), a, b, c - a, e - b, 0)
# hard hops: aggregate per node pair and sign
agg = {}
def pt(p): return ('FIX', p['fixed']) if 'fixed' in p else (p['node'], p['offset'])
for a, b in d['hard_hops']:
    (na, oa), (nb, ob) = pt(a), pt(b)
    if na not in free and nb not in free: continue
    e = agg.setdefault((na, nb), [na, nb, {}])     # FIX side: absolute point (its node position is 0)
    for sx in (-1, 1):
        for sy in (-1, 1):
            e[2][(sx, sy)] = max(e[2].get((sx, sy), -10**12), nm(sx * (oa[0] - ob[0]) + sy * (oa[1] - ob[1])))
hop_cons = 0
for key, (na, nb, mx) in agg.items():
    xa, ya = (0, 0) if na == 'FIX' else P[na][:2]; xb, yb = (0, 0) if nb == 'FIX' else P[nb][:2]
    for (sx, sy), c in mx.items():
        m.Add(sx * (xa - xb) + sy * (ya - yb) + c <= (IO_CAP.get(na if nb == 'FIX' else nb, R_IO) if 'FIX' in (na, nb) else R)); hop_cons += 1
# ring tiles
v = {}; ex = {}; xi = []; yi = []
def proj(half):                            # per sign: expression min over anchors of sx*px + sy*py (nm)
    hh = d['halves'][half]; refs = hh['anchor_refs']
    if hh['projection_min_nm'] is None: return None
    nodes = {r['node'] for r in refs}
    if not (nodes & set(free)):            # fixed nodes at their fulln origins
        return {(sx, sy): min(sx * (P[r['node']][0] + nm(r['offset'][0])) + sy * (P[r['node']][1] + nm(r['offset'][1])) for r in refs)
                for sx in (-1, 1) for sy in (-1, 1)}
    assert len(nodes) == 1, (half, nodes); n = nodes.pop()     # anchors follow their free station
    return {(sx, sy): sx * P[n][0] + sy * P[n][1] + nm(min(sx * r['offset'][0] + sy * r['offset'][1] for r in refs))
            for sx in (-1, 1) for sy in (-1, 1)}
for r in rings:
    x = m.NewIntVar(1, (W - TW) // U - 1, 'x' + r); y = m.NewIntVar(1, (H - TH) // U - 1, 'y' + r)
    f = m.NewBoolVar('mx' + r)
    yin = m.NewIntVar(0, H, ''); yout = m.NewIntVar(0, H, '')
    m.Add(yin == U * y).OnlyEnforceIf(f.Not()); m.Add(yout == U * y + TH).OnlyEnforceIf(f.Not())
    m.Add(yin == U * y + TH).OnlyEnforceIf(f); m.Add(yout == U * y).OnlyEnforceIf(f)
    v[r] = (x, y, f, yin, yout)
    ex[r] = m.NewIntVar(0, EXCESS, 'ex' + r); Rr = R + ex[r]
    xs = m.NewIntVar(0, W, ''); ys = m.NewIntVar(0, H, '')
    m.Add(xs == U * x - 5400); m.Add(ys == U * y - 5400)
    xi.append(m.NewFixedSizeIntervalVar(xs, TW + 10800, '')); yi.append(m.NewFixedSizeIntervalVar(ys, TH + 10800, ''))
    pw, pr = proj(r + '_w'), proj(r + '_r')
    for sx in (-1, 1):
        for sy in (-1, 1):
            if pw is not None: m.Add(sx * U * x + max(sx * TW, 0) + sy * yin - pw[(sx, sy)] <= Rr)
            if pr is not None: m.Add(sx * U * x + max(sx * TW, 0) + sy * yout - pr[(sx, sy)] <= Rr)
    mxp = (old[r + '_w'][0] + old[r + '_r'][0]) * 500; myp = (old[r + '_w'][1] + old[r + '_r'][1]) * 500
    for n in hard:                         # ring <-> hard 21.6
        if near(n, mxp, myp, 1300000): sep(U * x, U * y, TW, TH, *box(n), 21600)
    for (a, b, c, e) in sites:
        if abs((a + c) / 2 - mxp) + abs((b + e) / 2 - myp) > 900000: continue
        sep(U * x, U * y, TW, TH, a, b, c - a, e - b, 0)
m.AddNoOverlap2D(xi, yi)
for a, b in d['soft_edges']:               # r0: source ring tile out face -> destination ring tile in face
    ra, rb = a.rsplit('_', 1)[0], b.rsplit('_', 1)[0]
    xa, _, _, _, ya = v[ra]; xb, _, _, yb, _ = v[rb]
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.Add(sx * U * (xa - xb) + max(sx * TW, 0) + max(-sx * TW, 0) + sy * (ya - yb) <= R)
obj = []
for r in rings:
    x, y = v[r][:2]; pw, pr = old[r + '_w'], old[r + '_r']
    mx = round((pw[0] + pr[0]) / 2 * 1000 - TW / 2); my = round((pw[1] + pr[1]) / 2 * 1000 - TH / 2)
    dx = m.NewIntVar(0, W, ''); dy = m.NewIntVar(0, H, '')
    m.AddAbsEquality(dx, U * x - mx); m.AddAbsEquality(dy, U * y - my); obj += [dx, dy]
    m.AddHint(x, round(mx / U)); m.AddHint(y, round(my / U))
for n in free:
    dx = m.NewIntVar(0, W, ''); dy = m.NewIntVar(0, H, '')
    m.AddAbsEquality(dx, P[n][0] - hard[n]['X']); m.AddAbsEquality(dy, P[n][1] - hard[n]['Y']); obj += [4 * dx, 4 * dy]
m.Minimize(sum(obj) + 1000 * sum(ex.values()))
sol = cp_model.CpSolver(); sol.parameters.num_search_workers = int(os.environ.get('OT_RTPB_WORKERS', 8))
sol.parameters.max_time_in_seconds = float(os.environ.get('OT_RTPB_TIME_S', 1200)); sol.parameters.random_seed = 17
stt = sol.Solve(m)
res = {'status': sol.StatusName(stt), 'reach_um': REACH, 'io_reach_um': R_IO / 1000, 'move_um': MOVE / 1000, 'tile_um': [TW / 1000, TH / 1000],
       'lattice_um': U / 1000, 'mode': 'r0+free stations', 'hop_constraints': hop_cons, 'free_stations': len(free),
       'scope': 'ring tiles (r0: own output register) + free stn514/516 on 43.2; all hard hops, writer anchors -> tile in face, '
                'tile out face -> reader anchors, soft ring->ring edges <= reach; 21.6 hard/ring-hard, 10.8 ring-ring, 4.32 sites',
       'wall_time_s': sol.WallTime()}
if stt in (cp_model.OPTIMAL, cp_model.FEASIBLE):
    res['objective_um'] = sol.ObjectiveValue() / 1000
    res['reach_excess_um'] = {r: sol.Value(ex[r]) / 1000 for r in rings if sol.Value(ex[r])}
    res['tiles'] = {r: {'at': [sol.Value(v[r][0]) * U / 1000, sol.Value(v[r][1]) * U / 1000],
                        'orient': 'MX' if sol.Value(v[r][2]) else 'R0'} for r in rings}
    res['stations_moved'] = {n: [sol.Value(P[n][2]) * U / 1000, sol.Value(P[n][3]) * U / 1000] for n in free
                             if (sol.Value(P[n][2]) * U, sol.Value(P[n][3]) * U) != (hard[n]['X'], hard[n]['Y'])}
out_p.write_text(json.dumps(res, indent=1) + '\n')
print('RING_TILE_PLACE_B', res['status'], res.get('objective_um'), len(res.get('stations_moved', {})), res.get('reach_excess_um'), res['wall_time_s'])
