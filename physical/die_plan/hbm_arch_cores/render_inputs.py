#!/usr/bin/env python3
"""render core_tree_inputs.json: sinks (grey), macros, entry (red), tree nodes/legs (blue), leaf islands (green, label=load)."""
import json, sys, os
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(__file__))
from leaf_islands import load
d = json.load(open(sys.argv[1])); sd = sys.argv[2]; out = sys.argv[3]
ts = [t for t in d['types'] if 'tree' in t]
n = len(ts); cols = 5; rows = (n + cols - 1) // cols
fig, axs = plt.subplots(rows, cols, figsize=(cols * 5, rows * 5.4))
for ax, t in zip(axs.flat, ts):
    die, sinks, macros, pins = load(os.path.join(sd, t['module'] + '.txt'))
    W, H = t['plan_outline_um']; sx, sy = W / (die[2] - die[0]), H / (die[3] - die[1])
    ax.scatter([s[0] * sx for s in sinks], [s[1] * sy for s in sinks], s=0.2, c='0.6', rasterized=True)
    for m in macros:
        ax.add_patch(plt.Rectangle((m[0] * sx, m[1] * sy), (m[2] - m[0]) * sx, (m[3] - m[1]) * sy, fc='none', ec='orange', lw=0.6))
    pos = {('leaf%d' % i): l['xy_um'] for i, l in enumerate(t['leaf_islands'])}
    for nd in t['tree']['nodes']:
        pos[nd['name']] = nd['xy_um']
    for nd in t['tree']['nodes']:
        for c in nd['children']:
            a, b = nd['xy_um'], pos[c]
            ax.plot([a[0], b[0], b[0]], [a[1], a[1], b[1]], 'b-', lw=0.8)
    r = pos[t['tree']['root_node']]; e = t['clock_entry']['xy_um']
    ax.plot([e[0], r[0], r[0]], [e[1], e[1], r[1]], 'r-', lw=1.2)
    for l in t['leaf_islands']:
        ax.add_patch(plt.Rectangle((l['rect_um'][0], l['rect_um'][1]), 8.64, 8.64, fc='g', ec='k', lw=0.4))
        ax.text(l['xy_um'][0], l['xy_um'][1] + 6, '%d' % l['sinks'], fontsize=5, ha='center')
    ax.plot([e[0]], [e[1]], 'r*', ms=10)
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect('equal')
    b = t['balance']
    ax.set_title('%s\n%s nat %s ps, %d leaves, p95r<=%.0f, trunk %.0f-%.0f\n%s' % (
        t['module'][-34:], 'x'.join('%g' % v for v in (W, H)), t['measured_natural_tt_ps'], t['tree']['leaves'],
        max(l['p95_radius_um'] for l in t['leaf_islands']), b['trunk_min_um'], b['trunk_max_um'], t['coords'][:20]), fontsize=7)
for ax in list(axs.flat)[n:]:
    ax.axis('off')
plt.tight_layout(); plt.savefig(out, dpi=110)
print(out)
