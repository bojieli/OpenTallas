#!/usr/bin/env python3
"""S81-LP-2 review render: lane variant floorplans (macros, pins by face) + 4-across fit in the s_0S_LP slot with the
parent coll_i/coll_o S-face windows (plan_s13r2 buses)."""
import json, sys
from pathlib import Path
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
D = Path(sys.argv[1]); SZ = {'ot_sram_1r1w2c_32x64_m1': (31.992, 17.304), 'ot_sram_1r1w2c_256x64_m1': (34.584, 41.352)}
WIN = {'coll_i0': (6.144, 117.084), 'coll_i1': (119.04, 228.828), 'coll_i2': (663.744, 772.764), 'coll_i3': (776.64, 884.508),
       'coll_o0': (231.936, 343.26), 'coll_o1': (344.448, 455.772), 'coll_o2': (907.776, 1016.412), 'coll_o3': (1020.288, 1128.54)}
fig, ax = plt.subplots(1, 4, figsize=(22, 9), gridspec_kw=dict(width_ratios=[1, 1, 2.2, 2.2]))
for k, v in enumerate(['A', 'B']):
    s = json.load(open(D / v / 'spec.json')); pp = json.load(open(D / v / 'plan_pins.json'))
    w, h = s['outline']['w'], s['outline']['h']; a = ax[k]
    a.add_patch(Rectangle((0, 0), w, h, fill=False, lw=1.5))
    for m in s['macros']:
        mw, mh = SZ[m['view'].split('/')[-1]]; c = {'u_gb': 'tab:blue', 'u_ep.g_rb': 'tab:orange', 'u_ski': 'tab:green', 'u_ep.g_fi': 'tab:red'}
        col = next(cc for kk, cc in c.items() if m['inst'][1:].startswith(kk))
        a.add_patch(Rectangle(m['at'], mw, mh, color=col, alpha=.6)); a.plot([m['at'][0]] * 2, [m['at'][1], m['at'][1] + mh], 'k-', lw=1.2)
    for q in pp['pins']:
        n = q['name'].split('[')[0]; col = {'rx': 'b', 'tx': 'm', 'lo_d': 'g', 'li_d': 'r', 'ck': 'k'}.get(n, 'y')
        a.plot(q['x'], q['y'], '.', ms=2 if n != 'ck' else 10, color=col)
    a.set_title(f'{v}: {w} x {h} um (gb blue, rb orange, ski green, fifo red; black = SRAM pin edge)\nS rx blue / tx magenta, N lo green / li red, E ck black', fontsize=8)
    a.set_aspect('equal'); a.set_xlim(-10, w + 10); a.set_ylim(-10, h + 10)
    a = ax[2 + k]; W, H = 1442.88, 1226.88
    a.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5))
    gap = (W - 4 * w) / 4 if v == 'B' else (W - 4 * w) / 5
    xs = [gap / 2 + i * (w + gap) for i in range(4)] if v == 'B' else [gap + i * (w + gap) for i in range(4)]
    for i, x in enumerate(xs):
        a.add_patch(Rectangle((x, 30), w, h, color='tab:gray', alpha=.4)); a.text(x + w / 2, 30 + h / 2, f'u_u_ln{i}', ha='center')
        rx = [q['x'] for q in pp['pins'] if q['name'].startswith('rx')]; tx = [q['x'] for q in pp['pins'] if q['name'].startswith('tx')]
        a.plot([x + min(rx), x + max(rx)], [32, 32], 'b-', lw=3); a.plot([x + min(tx), x + max(tx)], [32, 32], 'm-', lw=3)
        a.annotate('', xy=(x + (min(rx) + max(rx)) / 2, 32), xytext=(sum(WIN[f'coll_i{i}']) / 2, 0), arrowprops=dict(arrowstyle='->', color='b'))
        a.annotate('', xy=(sum(WIN[f'coll_o{i}']) / 2, 0), xytext=(x + (min(tx) + max(tx)) / 2, 32), arrowprops=dict(arrowstyle='->', color='m'))
    for n, (x0, x1) in WIN.items():
        a.plot([x0, x1], [0, 0], '-', lw=6, color='b' if '_i' in n else 'm'); a.text((x0 + x1) / 2, -40, n, ha='center', fontsize=7)
    a.set_title(f's_0S_LP 1442.88 x 1226.88 with 4 lanes {v} (30-um S landing band); parent S windows coll_i blue / coll_o magenta', fontsize=8)
    a.set_aspect('equal'); a.set_xlim(-20, W + 20); a.set_ylim(-80, H + 20)
plt.tight_layout(); plt.savefig(D / 'lane_variants.png', dpi=110)
print(D / 'lane_variants.png')
