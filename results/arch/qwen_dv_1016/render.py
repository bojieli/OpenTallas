#!/usr/bin/env python3
"""Q-DV floorplan PNG: blocks + data links (width ~ bits), coloured by class.  render.py MODEL.json OUT.png [title]"""
import json, sys
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
d = json.load(open(sys.argv[1])); I = {i['n']: i for i in d['insts']}
cen = lambda i: (i['x'] + i['w'] / 2, i['y'] + i['h'] / 2)
cl = lambda i, P: (min(max(P[0], i['x']), i['x'] + i['w']), min(max(P[1], i['y']), i['y'] + i['h']))
COL = {'dv_reduce': '#d62728', 'dv_lane': '#ff7f0e', 'dv_gather': '#2ca02c', 'dv_ring': '#9467bd', 'dv_coll': '#8c564b',
       'dv_d2d': '#e377c2', 'head_chain': '#1f77b4', 'tree_spine': '#17becf'}
FILL = {'qfd_dv_slice': '#fde0c5', 'qfd_dv_redstn': '#f4a6a6', 'qfd_c_b16': '#eef5ee', 'qfd_dv_gather_exit': '#b6e3b6'}
fig, ax = plt.subplots(figsize=(22, 15.5))
for i in d['insts']:
    ax.add_patch(Rectangle((i['x'], i['y']), i['w'], i['h'], fc=FILL.get(i['m'], '#e8e8f4'), ec='#555', lw=.5))
    if i['w'] * i['h'] > 3e5 or i['m'] in FILL:
        ax.text(*cen(i), i['n'].replace('c16_', ''), ha='center', va='center', fontsize=6 if i['m'] != 'qfd_dv_slice' else 9)
for b, c, bits, eps in d['buses']:
    if c in ('clock_trunk', 'reset') or c not in COL: continue
    p = [I[e] for e in eps if e in I]
    for a, q in zip(p, p[1:]) if len(p) == 2 else [(p[0], t) for t in p[1:]]:
        A, Q = cl(a, cen(q)), cl(q, cen(a))
        ax.plot([A[0], Q[0]], [A[1], Q[1]], color=COL[c], lw=max(.4, bits / 500), alpha=.8)
for c, col in COL.items(): ax.plot([], [], color=col, lw=3, label=c)
ax.legend(loc='upper left', fontsize=9, ncol=4)
W = max(i['x'] + i['w'] for i in I.values()); H = max(i['y'] + i['h'] for i in I.values())
ax.set_xlim(0, W + 50); ax.set_ylim(0, H + 50); ax.set_aspect('equal')
ax.set_title(sys.argv[3] if len(sys.argv) > 3 else sys.argv[1], fontsize=11)
fig.savefig(sys.argv[2], dpi=90, bbox_inches='tight')
