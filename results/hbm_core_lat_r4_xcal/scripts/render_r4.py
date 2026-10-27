#!/usr/bin/env python3
"""render_r4.py PLACED_CSV MACRO_JSON SLICE_JSON OUT.png TITLE [PLAN_JSON]: placed core + macros(halo) + islands (+ planned tree nodes)."""
import csv, json, sys, collections
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
pc, mj, sj, out, title = sys.argv[1:6]
pj = sys.argv[6] if len(sys.argv) > 6 else None
SZ = {'ot_sram_1r1w_1024x256_m2_r2c2': (174.744, 70.488), 'ot_sram_1r1w_128x256_m1_r2c2': (94.824, 41.064)}
sl = json.load(open(sj)); W, H = sl['outline_um']
fig, ax = plt.subplots(figsize=(10, 10 * H / W))
ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5)); ax.add_patch(Rectangle((4.32, 4.32), W - 8.64, H - 8.64, fill=False, lw=0.5, ls='--'))
for m in json.load(open(mj))['macro_placement']:
    w, h = SZ[m['macro']]; x, y = m['origin_um']
    ax.add_patch(Rectangle((x - 2.16, y - 2.16), w + 4.32, h + 4.32, fc='#ddd', ec='none'))
    ax.add_patch(Rectangle((x, y), w, h, fc='#9ab', ec='k', lw=0.8)); ax.text(x + w / 2, y + h / 2, m['k'].split('.')[-1] + ' ' + m['orient'], ha='center', va='center', fontsize=8)
n = collections.Counter(); X = collections.defaultdict(list)
for r in csv.DictReader(open(pc)):
    k = r['kind']; n[k] += 1
    X[k].append((float(r['x']) + float(r['w']) / 2, float(r['y']) + float(r['h']) / 2))
col = {'ff': 'tab:red', 'buf': 'tab:green', 'std': 'tab:blue', 'face': 'tab:orange'}
for k, pts in X.items():
    if k == 'macro': continue
    ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=0.6 if k != 'ff' else 1.0, c=col.get(k, 'tab:gray'), label='%s %d' % (k, len(pts)), alpha=0.6, lw=0)
for i in sl['islands']:
    r = i['rect_um']; ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc='none', ec='magenta', lw=1.5)); ax.text(r[0], r[3] + 0.5, i['name'], color='magenta', fontsize=7)
    if 'clock_pin' in i: ax.plot(*i['clock_pin']['xy_um'], 'm*', ms=12)
if pj:
    p = json.load(open(pj)); pos = {nd[0]: nd[2] for nd in p['nodes']}
    for nd in p['nodes']:
        if nd[1] in pos:
            q = pos[nd[1]]; ax.plot([q[0], nd[2][0]], [q[1], nd[2][1]], '-', c='purple', lw=0.7, alpha=0.8)
    ax.scatter([nd[2][0] for nd in p['nodes']], [nd[2][1] for nd in p['nodes']], s=6, c='purple', zorder=5)
    ax.plot(*p['entry'], 'ks', ms=6)
ax.set_xlim(-2, W + 2); ax.set_ylim(-2, H + 2); ax.set_aspect('equal'); ax.legend(loc='upper right', fontsize=7, markerscale=8)
ax.set_title(title, fontsize=9); fig.tight_layout(); fig.savefig(out, dpi=130)
print(dict(n))
