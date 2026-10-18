#!/usr/bin/env python3
"""Q-DIEPLAN6: GEN floorplan PNG (rom_tp8b.json): blocks, relays (red), data links (face-projected, width ~ bits).
render_gen.py MODEL OUT.png TITLE [x0 y0 x1 y1]"""
import json, sys
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
d = json.load(open(sys.argv[1])); I = {i['n']: i for i in d['insts']}
cen = lambda i: (i['x'] + i['w'] / 2, i['y'] + i['h'] / 2)
cl = lambda i, P: (min(max(P[0], i['x']), i['x'] + i['w']), min(max(P[1], i['y']), i['y'] + i['h']))
box = [float(z) for z in sys.argv[4:8]] if len(sys.argv) > 7 else None
fig, ax = plt.subplots(figsize=(22, 17))
for i in d['insts']:
    rly = '_rly' in i['m'] or i['m'].startswith('qfd_rst_rep')
    ax.add_patch(Rectangle((i['x'], i['y']), i['w'], i['h'], fc='#d62728' if rly else
                           ('#fde0c5' if i['m'].startswith('qfd_dv_slice') else '#eef5ee' if i['m'].startswith('qfd_c_b16') else '#dde3f4'),
                           ec='#a00' if rly else '#555', lw=.4))
    if not rly and (i['w'] * i['h'] > 2e5 or (box and i['w'] * i['h'] > 5e3)):
        ax.text(*cen(i), i['n'], ha='center', va='center', fontsize=7, clip_on=True)
for b, c, bits, eps in d['buses']:
    if c in ('clock_trunk', 'reset'): continue
    p = [I[e] for e in eps if e in I]
    for a, q in (zip(p, p[1:]) if len(p) == 2 else [(p[0], t) for t in p[1:]]):
        A, Q = cl(a, cen(q)), cl(q, cen(a))
        ax.plot([A[0], Q[0]], [A[1], Q[1]], color='#1f77b4' if bits >= 64 else '#999', lw=max(.3, bits / 400), alpha=.7)
W = max(i['x'] + i['w'] for i in I.values()); H = max(i['y'] + i['h'] for i in I.values())
ax.set_xlim(*(box[0::2] if box else (0, W + 50))); ax.set_ylim(*(box[1::2] if box else (0, H + 50))); ax.set_aspect('equal')
ax.set_title(sys.argv[3], fontsize=11)
fig.savefig(sys.argv[2], dpi=80, bbox_inches='tight')
