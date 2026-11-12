"""svgr_top core render: macros (+halo), core margin, face pin density per bus; before | after. usage: CM_A CM_B PINS OUT"""
import json, sys, collections
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
a, b, pins, out = sys.argv[1:5]
W, H, M, HALO = 302.4, 639.36, 4.32, 4.32
pp = json.load(open(pins)); pp = pp['pins'] if isinstance(pp, dict) else pp
cols = {'sm_packet': '#d62828', 'sm_command': '#f77f00', 'seam_read_data': '#7b2cbf'}
fig, axs = plt.subplots(1, 2, figsize=(14, 15), facecolor='white')
for ax, (f, ttl) in zip(axs, ((a, 'BEFORE (d44v core_macros): DPL-0036, 568 cells unplaced'), (b, 'AFTER: u_program_lo -> (116.64, 434.7), R0, outline/pins unchanged'))):
    ms = json.load(open(f))['cores']['ot_svgr_top']['macros']
    ax.add_patch(Rectangle((0, 0), W, H, fc='#f7f7f7', ec='k'))
    ax.add_patch(Rectangle((M, M), W - 2 * M, H - 2 * M, fc='none', ec='#888', ls='--', lw=0.6))
    for m in ms:
        x0, y0, x1, y1 = m['rect_um']
        lo = m['name'].endswith('u_program_lo')
        ax.add_patch(Rectangle((x0 - HALO, y0 - HALO), x1 - x0 + 2 * HALO, y1 - y0 + 2 * HALO, fc='none', ec='#555', lw=0.5, ls=':'))
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc='#2a9d8f' if lo else '#bbbbbb', ec='k', lw=0.6))
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, m['name'].split('.')[-1] + ('' if 'cache' not in m['name'] else m['name'].split('g_cache')[1][:3]), fontsize=8, ha='center', va='center')
    for p in pp:
        bus = p['name'].split('[')[0]
        c = cols.get(bus)
        if c:
            ax.plot([p['x']], [p['y']], 's', ms=2, color=c)
    for k, c in cols.items():
        ax.plot([], [], 's', color=c, label=k)
    ax.legend(loc='upper center', fontsize=8)
    ax.set_xlim(-10, W + 10); ax.set_ylim(-10, H + 10); ax.set_aspect('equal'); ax.set_title(ttl, fontsize=9)
fig.suptitle('ot_svgr_top 302.4 x 639.36 (outline frozen): macro halo 4.32 (dotted), core margin 4.32 (dashed), failing face buses', fontsize=10)
fig.savefig(out, dpi=80, bbox_inches='tight')
