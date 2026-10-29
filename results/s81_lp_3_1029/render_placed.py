#!/usr/bin/env python3
"""S81-LP-3: render a placed lane kit (placed.csv from dump_placed.py) -> PNG: macros (grey), FF (blue), std (green),
buf/inv (orange), link pins S / core pins N (black ticks), ck entry (red star, from io.tcl).
    python3 render_placed.py KITDIR OUT.png"""
import csv, re, sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
kd, out = Path(sys.argv[1]), sys.argv[2]
die = re.search(r'DIE_AREA = 0 0 (\S+) (\S+)', (kd / 'config.mk').read_text())
W, H = float(die.group(1)), float(die.group(2))
ck = re.search(r'-pin_name \{ck\[0\]\} -layer \S+ -location \{(\S+) (\S+)\}', (kd / 'io.tcl').read_text())
rows = list(csv.DictReader(open(kd / 'placed.csv')))
fig, ax = plt.subplots(figsize=(7, 7 * H / W + 0.6), dpi=160)
ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1))
cnt = {}
for r in rows:
    k = r['kind']
    cnt[k] = cnt.get(k, 0) + 1
    x, y, w, h = (float(r[c]) for c in 'xywh')
    if k == 'macro':
        ax.add_patch(Rectangle((x, y), w, h, fc='0.75', ec='0.3', lw=0.4))
pts = {k: ([], []) for k in ('std', 'ff', 'buf')}
for r in rows:
    if r['kind'] in pts:
        pts[r['kind']][0].append(float(r['x']))
        pts[r['kind']][1].append(float(r['y']))
for k, c in (('std', 'tab:green'), ('buf', 'tab:orange'), ('ff', 'tab:blue')):
    ax.scatter(*pts[k], s=0.05, c=c, lw=0, label=f'{k} {len(pts[k][0])}')
px = [float(r['x']) for r in rows if r['kind'] == 'pin']
py = [float(r['y']) for r in rows if r['kind'] == 'pin']
ax.scatter(px, py, s=0.3, c='k', marker='s', lw=0, label=f'pins {len(px)}')
if ck:
    ax.plot(float(ck.group(1)), float(ck.group(2)), 'r*', ms=12, label='ck entry')
ax.set_xlim(-5, W + 5); ax.set_ylim(-5, H + 5); ax.set_aspect('equal')
ax.set_title(f'{kd.name} placed  {W}x{H}  macros {cnt.get("macro", 0)}', fontsize=8)
ax.legend(fontsize=6, markerscale=20, loc='upper right')
fig.tight_layout(); fig.savefig(out)
print(out, cnt)
