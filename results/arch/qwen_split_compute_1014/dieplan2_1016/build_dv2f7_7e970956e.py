#!/usr/bin/env python3
"""Q-DV dv2r8f7: dv2r8f6 on the Q-CLUSTER 43.2-um A0 origin lattice (claude/qcluster-1017 0fd5cb773): the outline
2,358.72 is 54.6 x 43.2, so abutting clusters cannot all sit on the lattice -> cluster pitch 2,376.0 (55 x 43.2,
17.28-um gap between clusters; slices keep the cluster pitch) unless Q-CLUSTER grows the outline to 2,376.0.
Band origins snapped UP to 43.2 multiples (everything above a band boundary shifts with it).
    python3 build_dv2f7.py IN(dv2r8f6).json OUT.json [PITCH]"""
import json, sys, math
src, out = sys.argv[1:3]; P = float(sys.argv[3]) if len(sys.argv) > 3 else 2376.0
LAT = 43.2
d = json.load(open(src)); I = {i['n']: i for i in d['insts']}
cl = {n: i for n, i in I.items() if n.startswith('c16_')}
up = lambda v: round(math.ceil(v / LAT - 1e-9) * LAT, 3)
# x: W half columns (g5..g0 from the W) and E half (E0..E5) -- keep the seam gap, re-pitch each half
xsW = sorted({round(i['x'], 2) for n, i in cl.items() if n.startswith('c16_W')})
xsE = sorted({round(i['x'], 2) for n, i in cl.items() if n.startswith('c16_E')})
x0W = up(xsW[0]); seam = xsE[0] - (xsW[-1] + cl['c16_W0_0']['w'])
x0E = up(x0W + 6 * P + seam - (P - cl['c16_W0_0']['w']))
def nx(x, xs, x0):
    k = min(range(len(xs)), key=lambda j: abs(xs[j] - x)); return round(x0 + k * P, 3)
# y: band origins snapped up, cumulative shift
bands = sorted({round(i['y'], 2) for i in cl.values()}); H = cl['c16_W0_0']['h']
shift = []; acc = 0.0
for b in bands:
    nb = up(b + acc); shift.append((b, nb - b)); acc = nb - b
def ny(y):
    s = 0.0
    for b, sh in shift:
        if y >= b - 1e-6: s = sh
    return round(y + s, 3)
for n, i in I.items():
    if n.startswith(('c16_W', 'dvs_W')): i['x'] = nx(i['x'], xsW, x0W)
    elif n.startswith(('c16_E', 'dvs_E')): i['x'] = nx(i['x'], xsE, x0E)
    elif n.startswith('dvl_') or n == 'die_margin_n': pass
    if n.startswith('c16_') or n.startswith('dvs_') or n == 'die_margin_n' or i['y'] > bands[1]:
        i['y'] = ny(i['y'])
# slices abut: bottom on band-1 top, height to band-2 bottom
b1 = I['c16_W0_1']; b2 = I['c16_W0_2']
for n, i in I.items():
    if n.startswith('dvs_'): i['y'] = round(b1['y'] + b1['h'], 3); i['h'] = round(b2['y'] - i['y'], 3); i['w'] = P   # slices one pitch wide: abut laterally
d['insts'] = list(I.values()); d['cluster_pitch'] = P; d['lattice'] = LAT; d['feedthrough_edges'] = 16
json.dump(d, open(out, 'w'))
C = [i for n, i in I.items() if n.startswith('c16_')]
off = sum(1 for i in C if abs(i['x'] / LAT - round(i['x'] / LAT)) > 1e-6 or abs(i['y'] / LAT - round(i['y'] / LAT)) > 1e-6)
Wd = max(i['x'] + i['w'] for i in I.values()) + 21.6; Hd = max(i['y'] + i['h'] for i in I.values()) + 21.6
print(out, 'pitch', P, 'off-lattice', off, 'die', round(Wd), 'x', round(Hd), round(Wd * Hd / 1e6, 1), 'mm2; slice h', I['dvs_W0']['h'])
