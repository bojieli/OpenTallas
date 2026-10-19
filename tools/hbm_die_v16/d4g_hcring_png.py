#!/usr/bin/env python3
"""HC-RINGPLAN 10-19: layout PNG of the GEN2d HC ring blocks (grants + plan) over the GEN2a placement.
    d4g_hcring_png.py MANIFEST.json OUT.png [--grants G] [--plan P]
Panel 1: whole die (GEN2a placed cells grey, grant slots orange, ring blocks red, re-packed slots green, b7->b0 joint
marked); panels 2-5: each quadrant's ring block +- 0.9 mm with bank names/orientations and neighbour slots."""
import argparse, json
from pathlib import Path
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / 'results/arch/hbm_die_d4g'
ap = argparse.ArgumentParser(); ap.add_argument('manifest'); ap.add_argument('out')
ap.add_argument('--grants', default=str(D / 'grants_d4g.json')); ap.add_argument('--plan', default=str(D / 'plan/d4g_phy/compact.P.json'))
a = ap.parse_args()
m = json.load(open(a.manifest)); PL = m['placement']; W, H = m['die_um']
g = json.load(open(a.grants)); P = json.load(open(a.plan))
slots = {s['name']: s for s in g['slots'] if s['kind'] != 'die' and s.get('origin') and s.get('outline')}
ring = {n for n, s in slots.items() if s.get('ring_block')}
moved = {n for n, s in slots.items() if 'HC-RINGPLAN' in (s.get('notes') or '') and n not in ring}
Q = ['SW', 'SE', 'NW', 'NE']


def draw(ax, x0, x1, y0, y1, lab):
    for n, p in PL.items():
        if n in slots or n.startswith(('hcb_', 'hcx_')) or n.split('_')[0] in ('hc',) and n[3:] in Q:
            continue
        if p['x'] < x1 and p['x'] + p['w'] > x0 and p['y'] < y1 and p['y'] + p['h'] > y0:
            ax.add_patch(Rectangle((p['x'], p['y']), p['w'], p['h'], fc='0.8', ec='0.5', lw=0.2))
    for n, r in P.items():
        if isinstance(r, dict) and 'x' in r and r['x'] < x1 and r['x'] + r['w'] > x0 and r['y'] < y1 and r['y'] + r['h'] > y0:
            ax.add_patch(Rectangle((r['x'], r['y']), r['w'], r['h'], fill=False, ec='royalblue', lw=0.4, ls='--'))
    for n, s in slots.items():
        X, Y, w, h = s['origin']['x'], s['origin']['y'], s['outline']['w'], s['outline']['h']
        if not (X < x1 and X + w > x0 and Y < y1 and Y + h > y0):
            continue
        c = 'red' if n in ring else ('limegreen' if n in moved else 'orange')
        ax.add_patch(Rectangle((X, Y), w, h, fc=c, alpha=0.45 if n in ring else 0.35, ec='k', lw=0.5))
        if lab and (n in ring or n in moved or w * h > 1.5e5):
            t = n + (f"\n{s['origin']['orient']} {s.get('kit', '').split('/')[-1].replace('hbm_hcq_', '')}" if n in ring else '')
            ax.text(X + w / 2, Y + h / 2, t, fontsize=6.5 if n in ring else 5.5, ha='center', va='center')
    if lab:
        for q in Q:   # b7 -> b0 abutment joint (chain closes, no die relay)
            if f'hcb_{q}0' in slots:
                b0 = slots[f'hcb_{q}0']['origin']
                ax.plot([b0['x'] + 60, b0['x'] + 674], [b0['y'], b0['y']], color='magenta', lw=2.5)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.tick_params(labelsize=6)


fig = plt.figure(figsize=(20, 14))
ax = fig.add_axes([0.01, 0.04, 0.30, 0.92]); draw(ax, 0, W, 0, H, False)
for q in Q:
    s = slots[f'hcb_{q}7']['origin']; ax.text(s['x'], s['y'] - 450, f'HC ring {q}', fontsize=7, color='darkred')
ax.set_title('HBM d4g GEN2d HC ring blocks (red) over GEN2a placement', fontsize=9)
pos = {'NW': [0.33, 0.52], 'NE': [0.67, 0.52], 'SW': [0.33, 0.03], 'SE': [0.67, 0.03]}
for q in Q:
    b7 = slots[f'hcb_{q}7']['origin']; X, Y = b7['x'], b7['y']; M = 900
    ax2 = fig.add_axes(pos[q] + [0.32, 0.44]); draw(ax2, X - M, X + 2203.2 + M, Y - M, Y + 2203.2 + M, True)
    ax2.set_title(f'{q} ring origin ({X:.1f}, {Y:.1f}), 3x734.4 um; magenta = b7->b0 abutment (no hcx relay)', fontsize=8)
fig.savefig(a.out, dpi=110); print(a.out)
