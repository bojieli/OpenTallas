#!/usr/bin/env python3
"""PATH-S81-PD4 render: the 53 re-routed lanes, PHY-fit ft_phy (left) vs PD4 direct lanes (right), on the PD2 B2 rects.
usage: render_pd4_lanes.py PLAN_B2C PLAN_PD4 ROUTES_JSON OUT_PNG"""
import json, sys
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
b2c, pd4, routes, out = sys.argv[1:5]
def rects(P):
    return {p['name']: (p['origin_um'][0], p['origin_um'][1], *P['partition_types'][p['type']]['outline_um']) for p in P['partitions']}
def paths(P, lids):
    pp = {p['id']: p for p in P['ports']}; L = {l['id']: l for l in P['lanes']}; res = {}
    for lid in lids:
        ps = [pp[x] for x in L[lid]['ports']]; res[lid] = ([ps[0]['src']['part']]+[p['dst']['part'] for p in ps], ps[0]['width'])
    return res
A = json.load(open(b2c)); B = json.load(open(pd4)); R = json.load(open(routes)); lids = [r['lane'] for r in R['routes']]
ra = rects(A); io = [i['rect_um'] for i in A['die']['io'] if i.get('part', '').startswith('lk_')]
fig, axs = plt.subplots(1, 2, figsize=(26, 10.5))
for ax, P, title in ((axs[0], A, 'PD2 B2 candidate: PHY-fit ft_phy chains (171,811 FT bits, svc_1/3/5/7 transits)'),
                     (axs[1], B, 'PD4: direct lanes, B5-preferred, no new svc transit, lk core-strip FT (%d FT bits)' % R['new_ft']['bits'])):
    for n, (x, y, w, h) in ra.items():
        fc = '#f3d9a4' if n.startswith('svc_') else '#cfe3f7' if n.startswith('lk_') else '#e6e6e6' if n.startswith(('fW', 'fE')) else 'white'
        ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec='#999999', lw=0.3))
        if n.startswith(('svc_', 'lk_', 'gunit', 'bk_sel', 'iqf', 'seqhost', 'phy_hbm')) or n.endswith(('_LP', '_C')):
            ax.text(x+w/2, y+h/2, n, fontsize=4.5, ha='center', va='center')
    for r in io: ax.add_patch(Rectangle((r[0], r[1]), r[2]-r[0], r[3]-r[1], fc='#7fa7d6', ec='none', alpha=0.6))
    for lid, (path, w) in paths(P, lids).items():
        xs = [ra[n][0]+ra[n][2]/2 for n in path]; ys = [ra[n][1]+ra[n][3]/2 for n in path]
        col = 'red' if any(n.startswith('svc_') for n in path[1:-1]) else 'tab:green' if 'gunit' in lid or 'WS3' in lid else 'tab:blue'
        ax.plot(xs, ys, '-', color=col, lw=0.4+w/400, alpha=0.7)
    ax.set_xlim(0, 31951); ax.set_ylim(0, 24745); ax.set_aspect('equal'); ax.set_title(title, fontsize=10)
fig.text(0.5, 0.02, 'lines = lane partition chains (centre to centre), width ~ bits; red = transits svc_*, green = gunit / lk_WS3 lanes (moved by PHY fit), blue = others; blue boxes = published PHY macros', ha='center', fontsize=9)
plt.tight_layout(rect=(0, 0.04, 1, 1)); plt.savefig(out, dpi=110)
