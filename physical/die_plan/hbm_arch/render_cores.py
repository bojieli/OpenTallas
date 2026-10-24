#!/usr/bin/env python3
"""HBM-ARCH G1 aid: per-type hard-core / soft-leaf placement render (check.py's die render does not draw contents).
    python3 render_cores.py PLAN.json OUT.png type1,type2,..."""
import json, sys, os, collections
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plan_p, out, types = sys.argv[1], sys.argv[2], sys.argv[3].split(',')
P = json.load(open(plan_p)); d = os.path.dirname(plan_p)
n = len(types); cols = min(3, n); rows = (n + cols - 1) // cols
fig, axs = plt.subplots(rows, cols, figsize=(7 * cols, 6.5 * rows), squeeze=False)
col = dict(N='tab:red', S='tab:blue', E='tab:green', W='tab:orange')
for ax, tn in zip(axs.flat, types):
    t = P['partition_types'][tn]; W, H = t['outline_um']
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=2))
    hc = {c['inst'] for c in t.get('hard_cores', [])}
    for c in t['contents']:
        if 'origin_um' in c and c['inst'] not in hc and not any(h.startswith(c['inst'] + '_') for h in hc):
            ax.add_patch(Rectangle(c['origin_um'], *c['outline_um'], fc='0.85', ec='0.5', hatch='//', lw=0.5))
    for c in t.get('hard_cores', []):
        x, y = c['origin_um']; w, h = c['outline_um']
        ax.add_patch(Rectangle((x, y), w, h, fc='lightsteelblue', ec='navy', lw=0.6))
        try:
            pins = json.load(open(os.path.join(d, c['pins_file'])))
            xs = [x + p['x'] for p in pins[::25]]; ys = [y + p['y'] for p in pins[::25]]
            ax.plot(xs, ys, ',', color='crimson')
        except Exception:
            pass
        if w * h > 0.004 * W * H:
            ax.text(x + w / 2, y + h / 2, c['inst'].replace('u_', ''), fontsize=5, ha='center', va='center')
    for b in t.get('buses', []):
        pass
    ax.set_xlim(-0.03 * W, 1.03 * W); ax.set_ylim(-0.03 * H, 1.03 * H); ax.set_aspect('equal')
    ax.set_title(f"{tn} {W:g}x{H:g} um: {len(hc)} hard cores (pins red, 1/25 drawn), soft leaves hatched", fontsize=8)
for ax in list(axs.flat)[n:]:
    ax.axis('off')
fig.tight_layout(); fig.savefig(out, dpi=140)
