#!/usr/bin/env python3
"""DIE-LAYOUT-HBM 11-11 (COORD GEOM note): hub->sm2 L8340 / L8340m (1615 b) off the W-running bank row.
Today: hub S -> b102 N, b102 W exit -> b111 -> b103 -> sm2 N at x 4235-4524 (10 stations, 12 cyc).
New: hub S -> b102 N -> b102 S (vertical, stations solved off cores by ladder.solve_slot) -> sm2 N at local x
5420-5690 (b102|sm2 overlap, 5.98 b/um); the b111 and b103 slots are deleted.  Cycle-exact: fixed_cycles = old
cycles - new natural (receiver pad lands identically in NW_sm2 and NE_sm2, same type q_sm2).
usage: r8340.py TOOLS IN.json OUT.json"""
import json, sys, os
TOOLS, INP, OUTP = sys.argv[1:4]
sys.argv = [sys.argv[0], TOOLS]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ladder as LD
S, LA = LD.S, LD.LA
raw = json.load(open(INP))
T = raw['partition_types']; parts = {p['name']: p for p in raw['partitions']}
PT = {p['id']: p for p in raw['ports']}; LN = {l['id']: l for l in raw['lanes']}
SMWIN = [5420.0, 5690.0]
lat = raw['latency']['lanes']
old = {l: int(lat[l]['cycles']) for l in ('L8340', 'L8340m')}
B = LA.Builder(raw, guard_um=2.0); P = B.P
smb = LD.bus_of(T['q_sm2'], 'L32_i'); smb['window_um'] = list(SMWIN)
rep = {}
for lid, q in (('L8340', 'NW'), ('L8340m', 'NE')):
    ln = LN[lid]; p0, p1, p2, p3 = (PT[i] for i in ln['ports'])
    b102 = q + '_b102'; tb = T[parts[b102]['type']]
    sl = LD.slot_of(tb, p0['dst']['bus'])
    # die windows: in = existing N window; out = sm2 window mapped to die
    fi, wi, _, _ = P.geom_to_die(b102, (sl['in_face'], sl['in_window_um'], sl['in_layers'], 'lsb_low'))
    fs, ws, _, _ = P.geom_to_die(q + '_sm2', ('N', SMWIN, ['M7', 'M5'], 'lsb_low'))
    lo, hi = sorted(ws)
    x0, y0, x1, y1 = P.rect(b102)
    assert x0 <= lo and hi <= x1, (b102, ws, x0, x1)
    got = LD.solve_slot(B, b102, fi, wi, 'S', [lo, hi])
    assert got, lid
    k, regs, Lr = got
    KF = int(os.environ.get('KFORCE', 0))     # same station count in NW and NE -> identical q_sm2 receiver pad
    if KF and k < KF:
        a = LA.Builder.face_pt(P, b102, fi, wi); bb = LA.Builder.face_pt(P, b102, 'S', [lo, hi])
        g2 = LD.slot_dp(B, b102, a, abs(wi[1] - wi[0]) / 2.0, bb, KF - 1)
        assert g2 is not None and len(g2) + 1 == KF, (lid, KF)
        k, regs = KF, [regs[0]] + g2
    of, owin, _fl = LD.type_window(P, b102, 'S', [lo, hi])
    sl['out_face'] = of
    sl['out_window_um'] = [LD.r4(v) for v in sorted(owin)]
    sl['out_layers'] = ['M7', 'M5']
    sl['stations'] = k
    sl['regs_um'] = [[LD.r4(v) for v in P.to_type(b102, r)] for r in regs]
    for kk in ('bit_sites_um', 'bit_site_cell_um'): sl.pop(kk, None)
    sl['note'] = (sl.get('note', '') + ' | DIE-LAYOUT-HBM 11-11 L8340 off the bank row: b102 N -> S straight into sm2').strip(' |')
    # drop the b111 / b103 slots
    for pp in (p1, p2):
        tt = T[parts[pp['dst']['part']]['type']]
        s2 = LD.slot_of(tt, pp['dst']['bus'])
        tt['ft_slots'].remove(s2)
    # ports: p1 now b102 -> sm2
    p1['dst'] = dict(p3['dst'])      # port geometry comes from the src slot (schema)
    raw['ports'] = [p for p in raw['ports'] if p['id'] not in (p2['id'], p3['id'])]
    ln['ports'] = [p0['id'], p1['id']]
    rep[lid] = dict(stations=k, route_um=round(Lr), regs=len(regs))
P2 = S.Plan(raw)
for lid in ('L8340', 'L8340m'):
    LN[lid].pop('fixed_cycles', None)
    nat = P2.lane_latency(lid)['natural']
    if old[lid] > nat:
        LN[lid]['fixed_cycles'] = old[lid] - nat
P3 = S.Plan(raw)
for lid in ('L8340', 'L8340m'):
    lat[lid] = dict(P3.lane_latency(lid), param=lat[lid].get('param', 'LAT_' + lid.upper()))
    rep[lid]['latency'] = lat[lid]
open(OUTP, 'w').write(json.dumps(raw, indent=1) + '\n')
print(json.dumps(rep, indent=1))
