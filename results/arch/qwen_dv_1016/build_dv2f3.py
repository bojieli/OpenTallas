#!/usr/bin/env python3
"""Q-DV dv2r8f3: dv2r8f2 re-pitched to the Q-CLUSTER DV cluster contract (claude/qcluster-1017 6d8a5581b,
results/arch/qwen_cluster_1017/cluster_contract_dv.json): qfd_c_b16_dv 2,358.72 x 5,227.2 um, cluster origins on the
8.64-um lattice, >= 86.4 um die margin above band 3 (N-face pins), no die link across a cluster outline.
Re-stack: y is stretched piecewise (each band below a point adds its height growth), x re-pitched; everything else
keeps its offsets.  python3 build_dv2f3.py IN(dv2r8f2).json OUT.json"""
import json, sys, math
src, out = sys.argv[1:3]
CW, CH, LAT, TOPM = 2358.72, 5227.2, 8.64, 86.4
d = json.load(open(src)); I = {i['n']: i for i in d['insts']}
I.pop('die_margin_n', None)
cl = {n: i for n, i in I.items() if n.startswith('c16_')}
ow, oh = next(iter(cl.values()))['w'], next(iter(cl.values()))['h']
xs = sorted({round(i['x'], 2) for i in cl.values()}); x0 = xs[0]
bands = sorted({round(i['y'], 2) for i in cl.values()})          # 4 band origins
snap = lambda v: round(math.ceil(v / LAT - 1e-9) * LAT, 3)
dh = CH - oh
def ny(y):                                                          # piecewise stretch
    return y + dh * sum(1 for b in bands if y >= b + oh - 1e-6)
nx0 = snap(x0); dx0 = nx0 - x0
for n, i in I.items():
    if n.startswith(('c16_', 'dvs_')):
        k = min(range(len(xs)), key=lambda j: abs(xs[j] - i['x']))
        i['x'] = round(nx0 + k * CW, 3); i['w'] = CW
        if n.startswith('c16_'):
            i['y'] = snap(ny(i['y'])); i['h'] = CH
        else:
            i['y'] = round(ny(i['y']), 3)
    else:
        if i['x'] >= x0 - 1:
            i['x'] = round(nx0 + (i['x'] - x0) * CW / ow, 3)
        i['y'] = round(ny(i['y']), 3)
top3 = max(i['y'] + i['h'] for n, i in I.items() if n.startswith('c16_'))
I['die_margin_n'] = dict(n='die_margin_n', m='outline_marker', x=nx0, y=round(top3 + TOPM - 21.6 - 1.0, 3), w=1.0, h=1.0)
d['insts'] = list(I.values()); d['cluster_w'] = CW; d['cluster_h'] = CH; d['cluster_contract'] = 'claude/qcluster-1017 6d8a5581b'
json.dump(d, open(out, 'w'))
W = max(i['x'] + i['w'] for i in I.values()) + 21.6; H = max(i['y'] + i['h'] for i in I.values()) + 21.6
off = [n for n, i in cl.items() if abs(i['x'] / LAT - round(i['x'] / LAT)) > 1e-6 or abs(i['y'] / LAT - round(i['y'] / LAT)) > 1e-6]
print(out, 'die', round(W), 'x', round(H), round(W * H / 1e6, 1), 'mm2; off-lattice clusters', len(off), '; top margin', round(H - top3, 1))
