#!/usr/bin/env python3
"""Render a dump_layout.tcl dump: cell classes, pins (clock pins red), and a 5-um cell-density heatmap.
usage: render_layout.py DUMP OUT.png [--title T] [--hi REGEX]  (--hi: highlight instances whose name matches)"""
import argparse, re
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument('dump'); ap.add_argument('out'); ap.add_argument('--title', default='')
ap.add_argument('--hi', action='append', default=[]); a = ap.parse_args()
die = None; insts = []; pins = []
for l in open(a.dump):
    t = l.split()
    if t[0] == 'DIE': die = list(map(float, t[1:5]))
    elif t[0] == 'I': insts.append((t[1], *map(float, t[2:6]), t[6] if len(t) > 6 else ''))
    elif t[0] == 'P': pins.append((float(t[1]), float(t[2]), t[3], t[4]))
W, H = die[2] - die[0], die[3] - die[1]
fig, ax = plt.subplots(1, 2, figsize=(14, 14 * H / max(W * 2, 1) + 1.5))
col = dict(std='#bbbbbb', ff='#3b78c2', latch='#2aa198', icg='#d33682', clkbuf='#dc322f', hold='#b58900', macro='#555555')
cnt = {}
his = [re.compile(h) for h in a.hi]
for c, x0, y0, x1, y1, n in insts:
    cnt[c] = cnt.get(c, 0) + 1
    hl = any(h.search(n) for h in his)
    ax[0].add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, color='#ff7f0e' if hl else col.get(c, '#999'), lw=0,
                                  alpha=0.9 if c != 'std' else 0.5))
for x, y, s, n in pins:
    ax[0].plot(x, y, 's', ms=2.5, color='red' if s == 'CLOCK' or re.search(r'clk|^ck', n) else 'k')
ax[0].set_xlim(die[0], die[2]); ax[0].set_ylim(die[1], die[3]); ax[0].set_aspect('equal')
ax[0].set_title(f"{a.title}\n" + ' '.join(f"{k}:{v}" for k, v in sorted(cnt.items())), fontsize=8)
b = 5.0; nx, ny = max(1, int(W / b)), max(1, int(H / b)); g = np.zeros((ny, nx))
for c, x0, y0, x1, y1, n in insts:
    if c == 'macro': continue
    i = min(nx - 1, int((x0 + x1) / 2 / b)); j = min(ny - 1, int((y0 + y1) / 2 / b)); g[j, i] += (x1 - x0) * (y1 - y0)
im = ax[1].imshow(g / (b * b), origin='lower', extent=die and [die[0], die[0] + nx * b, die[1], die[1] + ny * b], vmin=0, vmax=1, cmap='inferno')
ax[1].set_title('cell area density per 5x5 um bin', fontsize=8); fig.colorbar(im, ax=ax[1], fraction=0.03)
plt.tight_layout(); plt.savefig(a.out, dpi=110)
print('wrote', a.out, cnt)
