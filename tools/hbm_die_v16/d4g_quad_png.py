#!/usr/bin/env python3
"""H-D4G GEN2 10-18: per-quadrant plan PNGs from the d4g grants (every slot with origin + outline, orientation marked)
over the plan blocks (plan/d4g_phy/compact.P.json), for the visual geometry check (owner rule: inspect die layouts).
    d4g_quad_png.py --grants G.json --plan P.json --out DIR [--box name=x0,y0,x1,y1 ...] [--hl RE]"""
import argparse, json, re
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ap = argparse.ArgumentParser(); ap.add_argument('--grants', required=True); ap.add_argument('--plan', required=True)
ap.add_argument('--out', required=True); ap.add_argument('--box', action='append', default=[])
ap.add_argument('--hl', default=r'^(coll|collg|collr|collk|collb|sfucore|sfup|cij|host_ep|host_cp)')
a = ap.parse_args()
g = json.load(open(a.grants)); P = json.load(open(a.plan))
P = P.get('blocks', P) if isinstance(P, dict) else P
die = next(s for s in g['slots'] if s['kind'] == 'die'); W, H = die['outline']['w'], die['outline']['h']
boxes = {'SW': (0, 0, W / 2, H / 2), 'SE': (W / 2, 0, W, H / 2), 'NW': (0, H / 2, W / 2, H), 'NE': (W / 2, H / 2, W, H),
         'die': (0, 0, W, H)}
for b in a.box:
    n, v = b.split('='); boxes[n] = tuple(float(x) for x in v.split(','))
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
hl = re.compile(a.hl)
SL = {s['name']: s for s in g['slots']}


def absxy(s):
    """die coordinates of a slot: child slots (parent != die) carry parent-local origins (R0 parents only)"""
    x, y = s['origin']['x'], s['origin']['y']
    p = SL.get(s.get('parent') or 'die')
    while p is not None and p['kind'] != 'die':
        x += p['origin']['x']; y += p['origin']['y']; p = SL.get(p.get('parent') or 'die')
    return x, y


for name, (x0, y0, x1, y1) in boxes.items():
    fig, ax = plt.subplots(figsize=(9, 9 * (y1 - y0) / (x1 - x0) if name != 'die' else 13), dpi=170)
    for n, r in P.items():
        if not isinstance(r, dict) or 'x' not in r:
            continue
        if r['x'] > x1 or r['x'] + r['w'] < x0 or r['y'] > y1 or r['y'] + r['h'] < y0:
            continue
        ax.add_patch(Rectangle((r['x'], r['y']), r['w'], r['h'], fill=True, fc='#eef3fb', ec='#9db4d8', lw=0.4))
        if name != 'die':
            ax.text(r['x'] + 4, r['y'] + r['h'] - 4, n, fontsize=3.2, color='#5d7bb0', va='top', clip_on=True)
    for s in g['slots']:
        o, w = s.get('origin'), s.get('outline')
        if not o or not w or s['kind'] == 'die':
            continue
        x, y, ww, hh = absxy(s)[0], absxy(s)[1], w['w'], w['h']
        if x > x1 or x + ww < x0 or y > y1 or y + hh < y0:
            continue
        h_ = bool(hl.search(s['name']))
        ax.add_patch(Rectangle((x, y), ww, hh, fill=True, fc='#ffd9a8' if h_ else '#e6e6e6', ec='#c05000' if h_ else '#555',
                               lw=0.6 if h_ else 0.3, alpha=0.85))
        orr = o.get('orient', 'R0')
        if name != 'die' or h_:
            ax.text(x + ww / 2, y + hh / 2, s['name'] + ('' if orr == 'R0' else f' [{orr}]'), fontsize=3.4 if name != 'die' else 2.2,
                    ha='center', va='center', color='#802000' if h_ else '#222', clip_on=True)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.tick_params(labelsize=5)
    ax.set_title(f'd4g GEN2 grants: {name}  ({Path(a.grants).name})', fontsize=7)
    fig.tight_layout(); fig.savefig(out / f'gen2_{name}.png'); plt.close(fig)
print('wrote', sorted(boxes))
