"""Render the planned hard cores and declared clock taps of an HBM v2 die_plan.json (HBM-P3-TAPS).
usage: render_cores_v2.py die_plan.json out.png [PART,PART...]  (the optional list also writes out_pins.png)"""
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
            col = ('tab:orange' if not c.get('pins_file') else 'tab:red' if 'SPLIT' in c.get('note', '') else 'tab:blue')
            ax.add_patch(Rectangle((ox + min(a[0], b[0]), oy + min(a[1], b[1])), cw, ch, fc=col, alpha=0.35, lw=0.3,
                                   ec=col))
        for tp in t['clock'].get('taps', []):
            x, y = tf(o, w, h, *tp['xy'])
            ax.plot(ox + x, oy + y, marker='*' if tp['kind'] == 'core' else ('^' if tp['kind'] == 'glue' else 's'),
                    ms=3 if not zoom else 6, color={'core': 'darkred', 'glue': 'green', 'leaf': 'purple'}[tp['kind']])
        x, y = tf(o, w, h, *t['clock']['tap_um'])
        ax.plot(ox + x, oy + y, marker='o', ms=2 if not zoom else 5, color='k')


import os
PD = os.path.dirname(os.path.abspath(sys.argv[1]))


def pins_zoom(ax, pname, step=4):
    """one partition, its cores and every step-th core pin (M4 green, M5 magenta) in the partition frame (R0 type)."""
    p = [q for q in plan['partitions'] if q['name'] == pname][0]
    t = T[p['type']]; w, h = t['outline_um']
    ax.add_patch(Rectangle((0, 0), w, h, fill=False, lw=0.8, ec='k'))
    n = 0
    for c in t.get('hard_cores', []):
        x0, y0 = c['origin_um']; cw, ch = c['outline_um']
        col = ('tab:orange' if not c.get('pins_file') else 'tab:red' if 'SPLIT' in c.get('note', '') else 'tab:blue')
        ax.add_patch(Rectangle((x0, y0), cw, ch, fc=col, alpha=0.2, lw=0.4, ec=col))
        ax.text(x0 + 4, y0 + ch / 2, c['inst'], fontsize=4)
        if c.get('pins_file'):
            pins = json.load(open(os.path.join(PD, c['pins_file'])))
            n += len(pins)
            pp = pins[::step]
            ax.scatter([x0 + q['x'] for q in pp], [y0 + q['y'] for q in pp], s=0.15, lw=0,
                       c=['green' if q['layer'] == 'M4' else 'm' for q in pp])
    ax.set_xlim(-20, w + 20); ax.set_ylim(-20, h + 20); ax.set_aspect('equal')
    ax.set_title(f'{pname} ({p["type"]}): {len(t.get("hard_cores", []))} cores, {n} core pins (every {step}th drawn; '
                 'M4 green E/W, M5 magenta N/S)', fontsize=8)


if len(sys.argv) > 3:                               # HBM-P5-PINS: pin zoom of named partitions
    zs = sys.argv[3].split(',')
    fig, axs = plt.subplots(1, len(zs), figsize=(9 * len(zs), 12))
    for ax, z in zip(axs if len(zs) > 1 else [axs], zs):
        pins_zoom(ax, z)
    plt.tight_layout(); plt.savefig(sys.argv[2].replace('.png', '_pins.png'), dpi=110)
fig, axs = plt.subplots(1, 2, figsize=(22, 18), gridspec_kw=dict(width_ratios=[1, 1]))
draw(axs[0], plan['partitions'])
axs[0].set_xlim(0, W); axs[0].set_ylim(0, H); axs[0].set_aspect('equal')
axs[0].set_title('HBM v2 hard cores (blue=pins, red=split core with plan pins, orange=NO pins); taps * core ^ glue s leaf')
nw = [p for p in plan['partitions'] if p['name'].startswith('NW_') or p['name'] == 'C0']
draw(axs[1], nw, zoom=True)
xs = [p['origin_um'][0] for p in nw]; ys = [p['origin_um'][1] for p in nw]
axs[1].set_xlim(min(xs) - 100, W / 2 + 1800); axs[1].set_ylim(min(ys) - 100, H); axs[1].set_aspect('equal')
axs[1].set_title('NW quadrant + C0 zoom')
plt.tight_layout(); plt.savefig(sys.argv[2], dpi=90)
