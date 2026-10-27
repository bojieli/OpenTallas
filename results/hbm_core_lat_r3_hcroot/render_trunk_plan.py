#!/usr/bin/env python3
"""HBM-CORE-LAT-R3 hcroot: render a placed core + its planned 12.8c fixed-trunk tree (plan JSON of core_trunk_plan.py).
    render_trunk_plan.py placed.csv pins.json plan.json OUT.png [title]
Draws: std cells (grey), flops (blue), pin faces (pins coloured by layer), centre clock entry + entry island (red),
trunk chain (red text), tree nodes / branch buffers (black), leaf drivers (orange) with their equal-count clusters
(convex hull of member sinks), and the planned point-to-point edges."""
import csv, json, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np

def hull(p):
    p = sorted(set(p))
    if len(p) < 3: return p
    def cr(o, a, b): return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
    lo, up = [], []
    for q in p:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], q) <= 0: lo.pop()
        lo.append(q)
    for q in reversed(p):
        while len(up) >= 2 and cr(up[-2], up[-1], q) <= 0: up.pop()
        up.append(q)
    return lo[:-1] + up[:-1]

def main(csvf, pinsf, planf, out, title=''):
    rows = list(csv.DictReader(open(csvf)))
    P = json.load(open(planf)); pins = json.load(open(pinsf))
    W, H = 155.52, 172.8
    fig, ax = plt.subplots(figsize=(11, 12))
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.2, ec='k'))
    ax.add_patch(Rectangle((4.32, 4.32), W - 8.64, H - 8.64, fill=False, lw=0.6, ec='grey', ls='--'))
    std = np.array([(float(r['x']), float(r['y'])) for r in rows if r['kind'] in ('std', 'buf')] or [(0, 0)])
    ff = np.array([(float(r['x']), float(r['y'])) for r in rows if r['kind'] == 'ff'] or [(0, 0)])
    ax.scatter(std[:, 0], std[:, 1], s=0.15, c='#bbbbbb', lw=0)
    ax.scatter(ff[:, 0], ff[:, 1], s=0.3, c='#3060c0', lw=0)
    pl = pins if isinstance(pins, list) else pins.get('pins', [])
    for q in pl:
        if (q.get('name') or q.get('bus')) == 'clk': continue   # clock pin moved to the centre entry (slice)
        x, y = (q.get('x'), q.get('y')) if 'x' in q else q.get('xy', (None, None))
        if x is None: continue
        ax.plot([x], [y], marker='s', ms=1.2, c=('#20a020' if q.get('layer') == 'M4' else '#a020a0'), lw=0)
    ex, ey = P['entry']
    ax.add_patch(Rectangle((ex - 4.32, ey - 4.32), 8.64, 8.64, fill=False, lw=1.5, ec='red'))
    ax.plot([ex], [ey], marker='*', ms=16, c='red')
    nodes = {n[0]: n for n in P['nodes']}
    for n in P['nodes']:
        if n[1] and n[1] in nodes:
            a, b = nodes[n[1]][2], n[2]
            ax.plot([a[0], b[0], b[0]], [a[1], a[1], b[1]], c='k', lw=0.8)
    for n in P['nodes']:
        kind = n[4]
        c = {'entry': 'red', 'branch': 'k', 'rep': 'm', 'leaf': 'orange', 'node': 'k'}.get(kind, 'k')
        ax.plot([n[2][0]], [n[2][1]], marker='o' if kind != 'leaf' else 'D', ms=4 if kind != 'leaf' else 6, c=c, mec='k', mew=0.4)
    t = P['trunk']; pr = P['pred']
    ax.text(ex + 5, ey + 5, 'entry + fixed trunk %d x %s\n(dont_touch, FIRM, entry island)' % (t['n'], t['cell']), color='red', fontsize=8)
    ax.set_xlim(-3, W + 3); ax.set_ylim(-3, H + 3); ax.set_aspect('equal')
    ax.set_title('%s\n12.8c SHALLOW_FIXED_TRUNK plan (PLAN MODEL, UNCHECKED): TT %.1f (trunk %.1f) win %.1f | FF %.1f (trunk %.1f) win %.1f\n'
                 'splits %s, %d sinks, leaf load %s, level len %s um' % (
                     title, pr['TT']['mean'], pr['TT']['trunk_ps'], pr['TT']['window'], pr['FF']['mean'], pr['FF']['trunk_ps'],
                     pr['FF']['window'], P['splits'], P['n_sinks'], P['leaf_load'], [round(x, 1) for x in P['level_len_um']]), fontsize=9)
    fig.tight_layout(); fig.savefig(out, dpi=110)

if __name__ == '__main__':
    main(*sys.argv[1:])
