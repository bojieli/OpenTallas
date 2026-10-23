#!/usr/bin/env python3
"""render sampled GCell overflow (usage - capacity, summed over M4-M9) of one or more die GRT probes side by side.
    gcell_overflow_png.py out.png label1=gcell_usage1.txt [label2=gcell_usage2.txt ...]"""
import sys, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, numpy as np
def load(p):
    gx = gy = None; L = {}
    for l in open(p):
        t = l.split()
        if t[0] == 'GRIDX': gx = [float(v) for v in t[1].split(',')]
        elif t[0] == 'GRIDY': gy = [float(v) for v in t[1].split(',')]
        elif t[0] == 'L':
            row = [tuple(map(float, c.split('/'))) for c in t[3:]]
            L.setdefault(t[1], []).append(row)
    ov = None; per = {}
    for ln, rows in L.items():
        a = np.array([[max(0, u - c) for c, u in r] for r in rows], float)
        per[ln] = a.sum(); ov = a if ov is None else ov + a
    return ov, per
args = sys.argv[2:]
fig, axs = plt.subplots(1, len(args), figsize=(6 * len(args), 7.5))
axs = np.atleast_1d(axs); mx = None; data = []
for a in args:
    lab, p = a.split('=', 1); ov, per = load(p); data.append((lab, ov, per)); mx = max(mx or 0, np.percentile(ov, 99.5))
for ax, (lab, ov, per) in zip(axs, data):
    im = ax.imshow(ov, origin='lower', cmap='hot_r', vmin=0, vmax=mx, aspect=33 / 26 * ov.shape[1] / ov.shape[0])
    ax.set_title(f'{lab}\nsampled overflow ' + ' '.join(f'{k}:{v/1e3:.0f}k' for k, v in sorted(per.items())), fontsize=8)
fig.colorbar(im, ax=list(axs), shrink=0.6); fig.savefig(sys.argv[1], dpi=110, bbox_inches='tight')
