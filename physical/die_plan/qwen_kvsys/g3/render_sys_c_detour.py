#!/usr/bin/env python3
"""PATH-KV-SYSC2: render the kv3_sys_c plan (whole partition + W/E turn-band crops) for GEOM review.
usage: render_sys_c_detour.py PLAN.json REPORT.json OUT_PREFIX   -> OUT_PREFIX_{full,W,E}.png"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'tools' / 'die_plan'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon
import schema as S

raw = S.load(sys.argv[1]); P = S.Plan(raw); t = P.types['kv3_sys_c']; W, H = t['outline_um']
rep = json.load(open(sys.argv[2])); pre = sys.argv[3]
dom = rep['pg_domain_type_um']; ko = rep['tap_keepout_um']
slot = next(s for s in t['ft_slots'] if s['name'] == 'ft1'); cw, ch = slot['bit_site_cell_um']
cols = ['#888', '#1f77b4', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#d62728', '#2ca02c', '#1f77b4', '#888', '#888']
taps = rep['taps']


def draw(ax, lw=0.4, ms=0.4, text=True):
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5))
    ax.add_patch(Rectangle(dom[:2], dom[2]-dom[0], dom[3]-dom[1], color='orange', alpha=.22, label='VDDPHY domain'))
    ax.add_patch(Rectangle(ko[:2], ko[2]-ko[0], ko[3]-ko[1], fill=False, ec='orange', ls='--', lw=1, label='tap keepout'))
    for c in t['contents']:
        ax.add_patch(Rectangle(c['origin_um'], *c['outline_um'], fill=False, ec='b', lw=1.2))
        if text: ax.text(c['origin_um'][0]+2, c['origin_um'][1]+c['outline_um'][1]-14, c['module'][:24], fontsize=5, color='b', clip_on=True)
    for j, st in enumerate(slot['bit_sites_um']):
        ax.scatter([p[0]+cw/2 for p in st], [p[1]+ch/2 for p in st], s=ms, c=cols[j], marker='s', lw=0)
    for s in rep['sampled']:
        p = s['path']; ax.plot([q[0] for q in p], [q[1] for q in p], 'g-', lw=lw, alpha=.7)
    for e in t['internal_stations']:
        pts = [e['from_um']] + e['regs_um'] + [e['to_um']]
        ax.plot([q[0] for q in pts], [q[1] for q in pts], 'm--o', ms=3, lw=.8)
    for tp in taps:
        x, y = tp['xy']; r = tp['radius_um']
        ax.plot(x, y, 'k+', ms=9, mew=1.5)
        if r > 0:
            ax.add_patch(Polygon([(x-r, y), (x, y+r), (x+r, y), (x, y-r)], closed=True, fill=False, ec='k', lw=.4, ls=':'))
        if text: ax.text(x+4, y+4, f"{tp['port']} {tp['planned_sinks']}/{tp['radius_um']:.0f}", fontsize=5, clip_on=True)
    rx, ry = rep['root']['clock_tap_um']; ax.plot(rx, ry, 'rx', ms=12, mew=2)
    if text: ax.text(rx+5, ry-14, 'clock+reset root', fontsize=6, color='r', clip_on=True)
    ax.set_aspect('equal')


fig, ax = plt.subplots(figsize=(18, 9)); draw(ax)
tr = rep['turn']
ax.set_title(f"kv3_sys_c PATH-KV-SYSC2: UCIe+4 SRAM (blue), VDDPHY (orange) + tap keepout (dashed); ft1 523b per-bit columns "
             f"W x{tr['W_band_x']} E x{tr['E_band_x']} ({tr['bits_per_um_W']}/{tr['bits_per_um_E']} b/um), stations coloured by stage "
             f"(turn: blue corner, green bank, red corner), max hop {rep['max_ft_hop_um']} out {rep['max_out_hop_um']}; "
             f"FWD magenta; taps + = port load/radius (L1 diamond); red X root", fontsize=7)
ax.legend(loc='lower right', fontsize=6); fig.savefig(pre+'_full.png', dpi=120, bbox_inches='tight')
for side, (x0, x1) in (('W', (300, 760)), ('E', (1400, 1860))):
    fig, ax = plt.subplots(figsize=(11, 13)); draw(ax, lw=.6, ms=2.5)
    ax.set_xlim(x0, x1); ax.set_ylim(330, 1000)
    ax.set_title(f"kv3_sys_c {side} turn band crop: per-bit columns, corner/bank/corner stations, taps, FWD", fontsize=8)
    fig.savefig(f'{pre}_{side}.png', dpi=120, bbox_inches='tight')
print('wrote', pre)
