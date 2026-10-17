#!/usr/bin/env python3
"""Q-DV dv2r8f2: dv2r8f re-pitched to the Q-CLUSTER cluster (claude/qcluster-1017 0131f6672,
results/arch/qwen_cluster_1017/SPEC.md: corridors A/T/B 129.6 um, qfd_c_b16 2,285.28 x 5,184 um, rs_i -> rs_o in
corridor T, 14-edge feedthrough, >= 64.8 um die margin above band 3).  Slices stay one cluster pitch wide (now
2,285.28) at the dv2r8f slice-row height.  python3 build_dv2f2.py IN(dv2r8f).json OUT.json [CW]"""
import json, sys
src, out = sys.argv[1:3]; CWN = float(sys.argv[3]) if len(sys.argv) > 3 else 2285.28
d = json.load(open(src)); I = {i['n']: i for i in d['insts']}
arr = sorted({round(i['x'], 1) for n, i in I.items() if n.startswith('c16_')})
x0 = arr[0]; CW0 = arr[1] - arr[0]
col = {x: k for k, x in enumerate(arr)}
for n, i in I.items():
    if n.startswith(('c16_', 'dvs_')):
        k = col[min(arr, key=lambda a: abs(a - i['x']))]
        i['x'] = round(x0 + k * CWN, 3); i['w'] = CWN
    elif i['x'] >= x0 - 1:                         # anything else inside the array span (relays): scale its offset
        i['x'] = round(x0 + (i['x'] - x0) * CWN / CW0, 3)
top3 = max(i['y'] + i['h'] for n, i in I.items() if n.startswith('c16_'))
I['die_margin_n'] = dict(n='die_margin_n', m='outline_marker', x=x0, y=round(top3 + 64.8 - 21.6 - 1.0, 3), w=1.0, h=1.0)
d['insts'] = list(I.values()); d['cluster_w'] = CWN; d['feedthrough_edges'] = 14
json.dump(d, open(out, 'w'))
W = max(i['x'] + i['w'] for i in I.values()) + 21.6; H = max(i['y'] + i['h'] for i in I.values()) + 21.6
print(out, 'die', round(W), 'x', round(H), round(W * H / 1e6, 1), 'mm2')
