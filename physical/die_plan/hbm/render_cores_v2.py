"""Render the planned hard cores and declared clock taps of an HBM v2 die_plan.json (HBM-P3-TAPS).
usage: render_cores_v2.py die_plan.json out.png"""
import json, sys, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plan = json.load(open(sys.argv[1]))
T = plan['partition_types']
W, H = plan['die']['outline_um']


def tf(o, w, h, x, y):
    return {"R0": (x, y), "MX": (x, h - y), "MY": (w - x, y), "R180": (w - x, h - y)}[o]


def draw(ax, parts, zoom=None):
    for p in parts:
        t = T[p['type']]; w, h = t['outline_um']; ox, oy = p['origin_um']; o = p['orient']
        ax.add_patch(Rectangle((ox, oy), w, h, fill=False, lw=0.6, ec='k'))
        if zoom:
            ax.text(ox + 20, oy + h - 120, p['name'], fontsize=6)
        for c in t.get('hard_cores', []):
            x0, y0 = c['origin_um']; cw, ch = c['outline_um']
            a = tf(o, w, h, x0, y0); b = tf(o, w, h, x0 + cw, y0 + ch)
            col = 'tab:red' if 'SPLIT' in c.get('note', '') else ('tab:blue' if c.get('pins_file') else 'tab:orange')
            ax.add_patch(Rectangle((ox + min(a[0], b[0]), oy + min(a[1], b[1])), cw, ch, fc=col, alpha=0.35, lw=0.3,
                                   ec=col))
        for tp in t['clock'].get('taps', []):
            x, y = tf(o, w, h, *tp['xy'])
            ax.plot(ox + x, oy + y, marker='*' if tp['kind'] == 'core' else ('^' if tp['kind'] == 'glue' else 's'),
                    ms=3 if not zoom else 6, color={'core': 'darkred', 'glue': 'green', 'leaf': 'purple'}[tp['kind']])
        x, y = tf(o, w, h, *t['clock']['tap_um'])
        ax.plot(ox + x, oy + y, marker='o', ms=2 if not zoom else 5, color='k')


fig, axs = plt.subplots(1, 2, figsize=(22, 18), gridspec_kw=dict(width_ratios=[1, 1]))
draw(axs[0], plan['partitions'])
axs[0].set_xlim(0, W); axs[0].set_ylim(0, H); axs[0].set_aspect('equal')
axs[0].set_title('HBM v2 hard cores (blue=as-built pins, orange=no pins, red=split proposal); taps * core ^ glue s leaf')
nw = [p for p in plan['partitions'] if p['name'].startswith('NW_') or p['name'] == 'C0']
draw(axs[1], nw, zoom=True)
xs = [p['origin_um'][0] for p in nw]; ys = [p['origin_um'][1] for p in nw]
axs[1].set_xlim(min(xs) - 100, W / 2 + 1800); axs[1].set_ylim(min(ys) - 100, H); axs[1].set_aspect('equal')
axs[1].set_title('NW quadrant + C0 zoom')
plt.tight_layout(); plt.savefig(sys.argv[2], dpi=90)
