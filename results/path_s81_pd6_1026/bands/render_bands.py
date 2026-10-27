#!/usr/bin/env python3
"""PATH-S81-PD6: render the shifted types (PD5 grey outline-dashed cores vs PD6 cores) with their composed storage bands.
usage: render_bands.py WT PLAN_PD5_COMPOSED SIDE_PD5 PLAN_PD6_COMPOSED SIDE_PD6 SHIFT_LEDGER OUT_PNG"""
import json, sys, math
wt, c5, s5, c6, s6, ledp, outp = sys.argv[1:8]
sys.path.insert(0, wt + '/tools/die_plan')
import reset_tree as RT
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R5, R6 = json.load(open(c5)), json.load(open(c6)); S5, S6 = json.load(open(s5))['collector'], json.load(open(s6))['collector']
led = json.load(open(ledp))
base = lambda R, n: R['partition_types'][n].get('landing_base_type', n)
f5 = {(base(R5, f['type']), f['bus']) for f in S5['placement_failures']}
f6 = {(base(R6, f['type']), f['bus']) for f in S6['placement_failures']}
pick = []
for b in sorted(led):
    n6 = sorted(n for n in R6['partition_types'] if base(R6, n) == b)
    if n6: pick.append((b, n6[0]))
nc = 4; nr = math.ceil(len(pick) / nc)
fig, axs = plt.subplots(nr, nc, figsize=(5 * nc, 6 * nr)); axs = axs.ravel()
for ax, (b, n6) in zip(axs, pick):
    t6 = R6['partition_types'][n6]; w, h = t6['outline_um']
    n5 = next((n for n in R5['partition_types'] if base(R5, n) == b), None)
    ax.add_patch(Rectangle((0, 0), w, h, fill=False, lw=1))
    if n5:
        for r in RT.blockages(R5['partition_types'][n5]):
            ax.add_patch(Rectangle((r[0], r[1]), r[2]-r[0], r[3]-r[1], fill=False, ec='k', ls='--', lw=.4))
    for r in RT.blockages(t6):
        ax.add_patch(Rectangle((r[0], r[1]), r[2]-r[0], r[3]-r[1], color='grey', alpha=.55))
    for k, bd in S6['types'][n6]['bands'].items():
        if bd.get('rect_um'):
            x0, y0, x1, y1 = bd['rect_um']
            new = (b, k) in f5
            ax.add_patch(Rectangle((x0, y0), x1-x0, y1-y0, color='red' if new else 'blue', alpha=.8))
    left = sorted(k for (bb, k) in f6 if bb == b)
    ax.set_xlim(-10, w+10); ax.set_ylim(-10, h+10); ax.set_aspect('equal')
    ax.set_title(f"{b[:34]}\nshift {led[b]['shift_um']} red=PD5-FAIL now placed\nstill FAIL {left}", fontsize=8)
for ax in axs[len(pick):]: ax.axis('off')
fig.suptitle(f"PATH-S81-PD6 band core shifts: PD5 {len(S5['placement_failures'])} FAIL -> PD6 {len(S6['placement_failures'])} FAIL (dashed = PD5 cores)")
fig.tight_layout(); fig.savefig(outp, dpi=70)
print('RENDER', outp, len(pick))
