#!/usr/bin/env python3
"""CPL-QC-2: render a cslate eval (--paths JSON) + plan type geometry.  usage: render_cs.py GEOM.json EVAL.json OUT.png TITLE"""
import json, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np

geo = json.load(open(sys.argv[1])); ev = json.load(open(sys.argv[2])); out = sys.argv[3]; title = sys.argv[4]
W, H = geo['outline']
G = 17.28
fig, axs = plt.subplots(1, 2, figsize=(16, 16 * H / W / 2 + 1.5) if H > W else (18, 9))
for k, ax in enumerate(axs):
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5))
    if k == 1:
        u = np.maximum(np.array(ev['_useH']), np.array(ev['_useV']))
        ax.imshow(u.T, origin='lower', extent=(0, u.shape[0] * G, 0, u.shape[1] * G), cmap='inferno_r', vmin=0, vmax=1.5,
                  alpha=0.85)
    for c in geo['cores']:
        x0, y0, x1, y1 = c['rect']
        big = (x1 - x0) * (y1 - y0) > 20000
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=(k == 0), fc='#dddddd' if big else '#c9e4c5',
                               ec='k', lw=0.8, hatch='//' if big and k == 0 else None))
        if big or k == 0:
            ax.text((x0 + x1) / 2, (y0 + y1) / 2, '%s\n%s' % (c['inst'].split('.')[-1][-18:], c['orient']),
                    ha='center', va='center', fontsize=7 if big else 4)
        for g in c['groups']:
            if g['n'] >= 64:
                ax.plot(*g['c'], 's', ms=4, color='tab:blue')
                if k == 0 and big:
                    ax.text(g['c'][0], g['c'][1], ' ' + g['bus'], fontsize=5, color='tab:blue')
    for b in geo['buses']:
        w0, w1 = b['window_um']
        f = b['face']
        if f in 'NS':
            yy = H if f == 'N' else 0
            ax.plot([w0, w1], [yy, yy], lw=5, color='tab:orange')
            ax.text((w0 + w1) / 2, yy + (12 if f == 'N' else -30), '%s %s' % (b['name'], b.get('width', '')), fontsize=5,
                    ha='center', color='tab:orange')
        else:
            xx = W if f == 'E' else 0
            ax.plot([xx, xx], [w0, w1], lw=5, color='tab:orange')
            ax.text(xx + (8 if f == 'E' else -8), (w0 + w1) / 2, b['name'], fontsize=5, rotation=90,
                    ha='left' if f == 'E' else 'right', color='tab:orange')
    if k == 0:
        mx = max(p[0] for p in ev['_paths']) if ev['_paths'] else 1
        for w, lab, pts in ev['_paths']:
            xs, ys = zip(*pts) if len(pts) > 1 else ([pts[0][0]], [pts[0][1]])
            ax.plot(xs, ys, lw=0.3 + 2.2 * w / mx, color='tab:red', alpha=0.45)
        for n, p in ev['_pos'].items():
            m = 'x' if n.startswith('u_ist_') else ('+' if n.startswith('u_ft_') else '.')
            ax.plot(p[0], p[1], m, color='purple', ms=4 if m != '.' else 2)
    tap = geo.get('tap_um')
    if tap:
        ax.plot(*tap, '*', ms=12, color='magenta')
    for bn, r in (geo.get('bands') or {}).items():
        if r:
            ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fill=True, fc='#a6d96a', alpha=0.5, ec='g', lw=0.5))
    ax.set_xlim(-60, W + 60); ax.set_ylim(-60, H + 60); ax.set_aspect('equal')
    ax.set_title(['placement, routed links (width ~ bits), regs x, pins squares, windows orange',
                  'cell use (max H/V demand / capacity), 0..1.5'][k], fontsize=8)
m = ev
fig.suptitle('%s\nbit-mm %s  overflow %s (over macro %s)  p99 use %s  worst Hline cut %s  worst Vline cut %s' % (
    title, m['bitmm'], m['overflow'], m['overflow_over_macro'], m['p99_use'], m['worst_cut_Hline']['ratio'],
    m['worst_cut_Vline']['ratio']), fontsize=9)
plt.tight_layout()
plt.savefig(out, dpi=110)
