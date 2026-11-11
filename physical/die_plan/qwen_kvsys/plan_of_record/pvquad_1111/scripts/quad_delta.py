#!/usr/bin/env python3
"""quad_delta.py PLAN_IN PLAN_OUT DELTA_OUT : CPL-KV-PV-3 pinwheel-quad re-slot of the 16 kv3_pv* types.
Same outline, same cores, same netlist (positions/orients only). Each group gK becomes a 2x2 quad of its 4 pairs
around its join (pair pin faces all point at the join street; pair pK feeds join face tsK, no ts bus crosses a pair).
Per group the quad image (R0/MX/MY/R180) is chosen so the join keeps its base orient exactly (no join M3 lattice
change); pair orients follow from the image, so pair x-mirror class == join x-mirror class (bit order rule A).
Core clock taps move rigidly with their core (in-core island travels with the slot). Stations/ft/reset sites are NOT
moved here: the die-owner re-derive does that (G0 counts them)."""
import json, os, sys
GAP = float(os.environ.get('GAP', '25.92')); JX = float(os.environ.get('JX', '302.4')); RQ = float(os.environ.get('RQ', '1365.12')); QY0 = float(os.environ.get('QY0', '43.2')); QY1 = float(os.environ.get('QY1', '734.4'))
FL = {'R0': (0, 0), 'MY': (1, 0), 'MX': (0, 1), 'R180': (1, 1)}
FI = {v: k for k, v in FL.items()}
def comp(a, b): return FI[(FL[a][0] ^ FL[b][0], FL[a][1] ^ FL[b][1])]
PW, PH, J = 380.16, 190.08, 172.8
WQ, HQ = 2 * PW + GAP, 2 * PH + 2 * 43.2 + J          # 786.24 x 639.36
# probe-tested id image (intel1 cpl-kv-pv-probe/probe/pv_v2_quad, snapped to the 8.64 lattice)
ID = {'p0': (0.0, 0.0, PW, PH, 'MX'), 'p3': (PW + GAP, 0.0, PW, PH, 'MX'),
      'p1': (0.0, 449.28, PW, PH, 'R0'), 'p2': (PW + GAP, 449.28, PW, PH, 'R0'),
      'j': (JX, 233.28, J, J, 'R0')}
QO = {0: (8.64, QY0), 1: (RQ, QY0), 2: (8.64, QY1), 3: (RQ, QY1)}
def inst(g, k): return 'pv__u_g%d_j' % g if k == 'j' else 'pvg%d_%s' % (g, k)
pin, pout, dout = sys.argv[1:4]
PL = json.load(open(pin)); D = {}
for tn, T in PL['partition_types'].items():
    if not tn.startswith('kv3_pv'): continue
    assert T['outline_um'] == [2160.0, 1520.64], tn
    assert RQ + WQ <= 2160.0 + 1e-6
    H = {h['inst']: h for h in T['hard_cores']}
    taps = [t for t in ((T.get('clock') or {}).get('taps') or []) if t.get('kind') == 'core' and '.' in t['name']]
    d = {}
    for g in range(4):
        img = H[inst(g, 'j')]['orient']; fx, fy = FL[img]
        for k, (lx, ly, w, h, o) in ID.items():
            x = WQ - lx - w if fx else lx; y = HQ - ly - h if fy else ly
            x, y = round(QO[g][0] + x, 4), round(QO[g][1] + y, 4)
            assert abs(x / 8.64 - round(x / 8.64)) < 1e-6 and abs(y / 8.64 - round(y / 8.64)) < 1e-6, (tn, g, k, x, y)
            c = H[inst(g, k)]; no = comp(img, o)
            ox, oy = c['origin_um']; bf = FL[c['orient']]; nf = FL[no]
            for t in taps:
                if t['name'].split('.', 1)[0] != c['inst']: continue
                ux, uy = t['xy'][0] - ox, t['xy'][1] - oy
                rx, ry = (w - ux if bf[0] else ux), (h - uy if bf[1] else uy)
                t['xy'] = [round(x + (w - rx if nf[0] else rx), 4), round(y + (h - ry if nf[1] else ry), 4)]
            c['origin_um'] = [x, y]; c['orient'] = no
            c['note'] = (c.get('note', '') + ' | ' if c.get('note') else '') + 'CPL-KV-PV-3 11-11 quad g%d img %s' % (g, img)
            d[c['inst']] = [x, y, no]
    # overlap check
    R = [(n, v[0], v[1], *(H[n]['outline_um'])) for n, v in d.items()]
    for i in range(len(R)):
        for j in range(i + 1, len(R)):
            a, b = R[i], R[j]
            if a[1] < b[1] + b[3] - 1e-6 and b[1] < a[1] + a[3] - 1e-6 and a[2] < b[2] + b[4] - 1e-6 and b[2] < a[2] + a[4] - 1e-6:
                raise SystemExit('overlap %s %s %s' % (tn, a[0], b[0]))
    D[tn] = d
    print(tn, 'joins', [H[inst(g, 'j')]['orient'] for g in range(4)], 'taps moved', sum(1 for t in taps))
json.dump(PL, open(pout, 'w'), indent=1); open(pout, 'a').write('\n')
json.dump(D, open(dout, 'w'), indent=1, sort_keys=True)
