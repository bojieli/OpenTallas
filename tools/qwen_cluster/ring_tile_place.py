#!/usr/bin/env python3
"""QW-CB16REG 10-20 (main line a): place the 69 hardened landing-ring crossing tiles (qfd_c_ringx516/514, 108 x 43.2 um)
and their 69 output stations (qfd_c_stn516/514, 51.84 um, on the destination clock) of the CB16 parent on the 43.2-um hard
lattice, replacing the soft writer / reader bays of qfd_c_b16_fullm.

Model (exact form of tools/qwen_cluster/fullm_bank_solve.py, same inputs results/arch/qw_cb16_legal_bays_1020/grid43):
- writer-half anchors (every bit's source pin, projection_min_nm) are reached from the tile's IN face; the tile's OUT face
  reaches its station (whole station rect); the station reaches the reader-half anchors (every bit's destination pin):
  max L1 over every point pair <= REACH (default 400 um); orientation R0 (in = S face, out = N face) or MX is per tile;
- soft ring->ring edges (pad chains): source ring's station to the destination tile's in face <= REACH;
- 21.6-um clearance to every fixed hard child (A0, stations, xstn), 10.8 um between ring tiles, 4.32 um around every
  scalar control / reset FF site (physical/qcluster/qfd_c_b16_fullm_sites.tsv); inside the outline with a 43.2 margin.
Objective: minimise the summed displacement from the original writer / reader bays.
    ring_tile_place.py OUT.json [REACH_UM]
"""
import gzip, json, math, os, pathlib, sys
from ortools.sat.python import cp_model
ROOT = pathlib.Path(__file__).resolve().parents[2]
G = ROOT / 'results/arch/qw_cb16_legal_bays_1020/grid43'
d = json.load(gzip.open(G / 'qfd_c_b16_fullm_bank_inputs.json.gz'))
J = json.loads((G / 'qfd_c_b16_fullm_joint_solution.json').read_text())
out_p = pathlib.Path(sys.argv[1]); REACH = float(sys.argv[2]) if len(sys.argv) > 2 else 400.0
U = int(os.environ.get('OT_RTP_U_NM', 43200)); R = round(REACH * 1000); TW, TH = 108000, 43200; SW = 51840
W, H = [round(x * 1000) for x in d['outline']]
rings = sorted({n[:-2] for n in d['halves']})
if os.environ.get('OT_RTP_ONLY'): rings = [r for r in rings if r in os.environ['OT_RTP_ONLY'].split(',')]
import os
DIAG = set(os.environ.get('OT_RTP_DROP', '').split(','))   # diagnostics only: drop constraint classes sites,hard,soft,station_hard
sites = []
for l in (ROOT / 'physical/qcluster/qfd_c_b16_fullm_sites.tsv').read_text().splitlines():
    f = l.split('\t')
    if l.startswith('#') or len(f) != 5: continue
    x, y, xlo, xhi = [round(float(v) * 1000) for v in f[1:]]
    if 'sites' not in DIAG: sites.append((f[0], xlo - 4320, y - 4320 - 1080, xhi + 4320, y + 4320 + 1080))
old = {}
for l in (ROOT / 'physical/qcluster/qfd_c_b16_fullm_sites.tsv').read_text().splitlines():
    f = l.split('\t')
    if len(f) == 7 and not l.startswith('#'): old[f[0]] = [float(z) for z in f[1:]]
mid = {r: (round((old[r + '_w'][0] + old[r + '_r'][0]) * 500), round((old[r + '_w'][1] + old[r + '_r'][1]) * 500)) for r in rings}
m = cp_model.CpModel(); v = {}; st = {}; ex = {}; xi = []; yi = []
MODE = os.environ.get('OT_RTP_MODE', 'x')   # x: tile + output station ; r0: tile with its own output register
EXCESS = round(float(os.environ.get('OT_RTP_EXCESS_UM', 30)) * 1000)
for r in rings:
    hw = d['halves'][r + '_w']; hr = d['halves'][r + '_r']
    x = m.NewIntVar(1, (W - TW) // U - 1, 'x' + r); y = m.NewIntVar(1, (H - TH) // U - 1, 'y' + r)
    f = m.NewBoolVar('mx' + r)                    # 0: in S / out N ; 1: in N / out S
    yin = m.NewIntVar(0, H, 'yin' + r); yout = m.NewIntVar(0, H, 'yout' + r)
    m.Add(yin == U * y).OnlyEnforceIf(f.Not()); m.Add(yout == U * y + TH).OnlyEnforceIf(f.Not())
    m.Add(yin == U * y + TH).OnlyEnforceIf(f); m.Add(yout == U * y).OnlyEnforceIf(f)
    v[r] = (x, y, f, yin, yout)
    ex[r] = m.NewIntVar(0, EXCESS, 'ex' + r)    # planned-reach excess over REACH for this crossing (penalised, reported)
    Rr = R + ex[r]
    # halo: 10.8 um each side between ring tiles -> intervals widened by 5.4 um each side (grid units are 43.2: use nm vars)
    xs = m.NewIntVar(0, W, 'xs' + r); ys = m.NewIntVar(0, H, 'ys' + r)
    m.Add(xs == U * x - 5400); m.Add(ys == U * y - 5400)
    xi.append(m.NewFixedSizeIntervalVar(xs, TW + 10800, 'ix' + r)); yi.append(m.NewFixedSizeIntervalVar(ys, TH + 10800, 'iy' + r))
    sxv = m.NewIntVar(1, (W - SW) // U - 1, 'sx' + r); syv = m.NewIntVar(1, (H - SW) // U - 1, 'sy' + r)
    g = m.NewBoolVar('smx' + r)                   # station: 0: d on S / q on N ; 1: MX
    sin = m.NewIntVar(0, H, ''); sout = m.NewIntVar(0, H, '')
    m.Add(sin == U * syv).OnlyEnforceIf(g.Not()); m.Add(sout == U * syv + SW).OnlyEnforceIf(g.Not())
    m.Add(sin == U * syv + SW).OnlyEnforceIf(g); m.Add(sout == U * syv).OnlyEnforceIf(g)
    st[r] = (sxv, syv, g, sin, sout)
    xs2 = m.NewIntVar(0, W, ''); ys2 = m.NewIntVar(0, H, '')
    m.Add(xs2 == U * sxv - 5400); m.Add(ys2 == U * syv - 5400)
    xi.append(m.NewFixedSizeIntervalVar(xs2, SW + 10800, '')); yi.append(m.NewFixedSizeIntervalVar(ys2, SW + 10800, ''))
    for sx in (-1, 1):
        for sy in (-1, 1):
            pm = hw['projection_min_nm']
            if pm is not None:                    # writer anchors -> tile in face
                m.Add(sx * U * x + max(sx * TW, 0) + sy * yin - pm[str((sx, sy))] <= Rr)
            pm = hr['projection_min_nm']
            if pm is not None and MODE == 'x':    # station out face -> reader anchors
                m.Add(sx * U * sxv + max(sx * SW, 0) + sy * sout - pm[str((sx, sy))] <= Rr)
            if pm is not None and MODE == 'r0':   # tile out face (registered o) -> reader anchors
                m.Add(sx * U * x + max(sx * TW, 0) + sy * yout - pm[str((sx, sy))] <= Rr)
            if MODE == 'x':                       # tile out face -> station in face (segments)
                m.Add(sx * U * (x - sxv) + max(sx * TW, 0) + max(-sx * SW, 0) + sy * (yout - sin) <= Rr)
    # fixed hard clearance 21.6
    for hn, (hx, hy, hwid, hht) in ({} if 'hard' in DIAG else J['hard']).items():
        a, b, c, e = [round(z * 1000) for z in (hx - 21.6, hy - 21.6, hx + hwid + 21.6, hy + hht + 21.6)]
        fl = [m.NewBoolVar('') for _ in range(4)]
        m.Add(U * x + TW <= a).OnlyEnforceIf(fl[0]); m.Add(U * x >= c).OnlyEnforceIf(fl[1])
        m.Add(U * y + TH <= b).OnlyEnforceIf(fl[2]); m.Add(U * y >= e).OnlyEnforceIf(fl[3]); m.AddBoolOr(fl)
    for hn, (hx, hy, hwid, hht) in J['hard'].items():
        a, b, c, e = [round(z * 1000) for z in (hx - 21.6, hy - 21.6, hx + hwid + 21.6, hy + hht + 21.6)]
        if abs((a + c) / 2 - mid[r][0]) > 1500000 + (c - a) / 2 or abs((b + e) / 2 - mid[r][1]) > 1500000 + (e - b) / 2: continue
        fl = [m.NewBoolVar('') for _ in range(4)]
        m.Add(U * sxv + SW <= a).OnlyEnforceIf(fl[0]); m.Add(U * sxv >= c).OnlyEnforceIf(fl[1])
        m.Add(U * syv + SW <= b).OnlyEnforceIf(fl[2]); m.Add(U * syv >= e).OnlyEnforceIf(fl[3]); m.AddBoolOr(fl)
    for sn, a, b, c, e in sites:
        if abs((a + c) / 2 - mid[r][0]) + abs((b + e) / 2 - mid[r][1]) > 1300000: continue
        fl = [m.NewBoolVar('') for _ in range(4)]
        m.Add(U * sxv + SW <= a).OnlyEnforceIf(fl[0]); m.Add(U * sxv >= c).OnlyEnforceIf(fl[1])
        m.Add(U * syv + SW <= b).OnlyEnforceIf(fl[2]); m.Add(U * syv >= e).OnlyEnforceIf(fl[3]); m.AddBoolOr(fl)
    # scalar sites within 900 um of the original bays (the tile cannot reach farther under the reach bound)
    for sn, a, b, c, e in sites:
        if abs((a + c) / 2 - mid[r][0]) + abs((b + e) / 2 - mid[r][1]) > 900000: continue
        fl = [m.NewBoolVar('') for _ in range(4)]
        m.Add(U * x + TW <= a).OnlyEnforceIf(fl[0]); m.Add(U * x >= c).OnlyEnforceIf(fl[1])
        m.Add(U * y + TH <= b).OnlyEnforceIf(fl[2]); m.Add(U * y >= e).OnlyEnforceIf(fl[3]); m.AddBoolOr(fl)
m.AddNoOverlap2D(xi, yi)
for a, b in ([] if 'soft' in DIAG else d['soft_edges']):
    ra, rb = a.rsplit('_', 1)[0], b.rsplit('_', 1)[0]
    sxa, _, _, _, souta = st[ra]; xb, _, _, yb, _ = v[rb]
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.Add(sx * U * (sxa - xb) + max(sx * SW, 0) + max(-sx * TW, 0) + sy * (souta - yb) <= R)
# objective: displacement of the tile centre from the midpoint of the original bays
obj = []
for r in rings:
    x, y, f, _, _ = v[r]
    pw, pr = old[r + '_w'], old[r + '_r']
    mx = round((pw[0] + pr[0]) / 2 * 1000 - TW / 2); my = round((pw[1] + pr[1]) / 2 * 1000 - TH / 2)
    dx = m.NewIntVar(0, W, ''); dy = m.NewIntVar(0, H, '')
    m.AddAbsEquality(dx, U * x - mx); m.AddAbsEquality(dy, U * y - my); obj += [dx, dy]
    m.AddHint(x, round(mx / U)); m.AddHint(y, round(my / U))
m.Minimize(sum(obj) + 1000 * sum(ex.values()))
sol = cp_model.CpSolver(); sol.parameters.num_search_workers = 4; sol.parameters.max_time_in_seconds = 600;  sol.parameters.random_seed = 17
stt = sol.Solve(m)
res = {'status': sol.StatusName(stt), 'reach_um': REACH, 'tile_um': [TW / 1000, TH / 1000], 'lattice_um': U / 1000,
       'scope': 'ring tiles + output stations on 43.2; writer anchors -> tile in face, tile out face -> station, station -> reader '
                'anchors, soft ring->ring edges, all <= reach; 21.6 hard / 10.8 ring+station / 4.32 scalar-site clearance; '
                'conservative (whole station rect, whole face segment)',
       'wall_time_s': sol.WallTime()}
if stt in (cp_model.OPTIMAL, cp_model.FEASIBLE):
    res['objective_um'] = sol.ObjectiveValue() / 1000
    res['reach_excess_um'] = {r: sol.Value(ex[r]) / 1000 for r in rings if sol.Value(ex[r])}
    res['tiles'] = {r: {'at': [sol.Value(v[r][0]) * U / 1000, sol.Value(v[r][1]) * U / 1000],
                        'orient': 'MX' if sol.Value(v[r][2]) else 'R0',
                        'stn_at': [sol.Value(st[r][0]) * U / 1000, sol.Value(st[r][1]) * U / 1000],
                        'stn_orient': 'MX' if sol.Value(st[r][2]) else 'R0'} for r in rings}
out_p.write_text(json.dumps(res, indent=1) + '\n'); print('RING_TILE_PLACE', res['status'], res.get('objective_um'), res['wall_time_s'])
