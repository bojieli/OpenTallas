import json, sys, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plans = sys.argv[1:-1]; out = sys.argv[-1]
fig, axs = plt.subplots(1, 2 * len(plans), figsize=(11 * len(plans), 10), gridspec_kw=dict(width_ratios=[1, 1.4] * len(plans)))
cols = dict(L12x1="tab:red", L48x11="tab:blue", L53x1="tab:green", L74x1="tab:orange")
for j, p in enumerate(plans):
    t = json.load(open(p + '/die_plan.json'))['partition_types']["q_b101"]; W, H = t['outline_um']
    for ax, zoom in ((axs[2 * j], None), (axs[2 * j + 1], (-5, 740, 200, 900))):
        ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5))
        for h in t['hard_cores']:
            x, y = h['origin_um']; w, hh = h['outline_um']
            ax.add_patch(Rectangle((x - 8.64, y - 8.64), w + 17.28, hh + 17.28, fc='0.9', ec='0.6', lw=.5, ls='--'))
            ax.add_patch(Rectangle((x, y), w, hh, fc='0.6', ec='k', lw=.6))
        for s in t['ft_slots']:
            for st in s.get('bit_sites_um') or []:
                a = np.array(st); ax.scatter(a[:, 0], a[:, 1], s=1.5, c=cols.get(s['name'], 'k'), marker='s', lw=0, zorder=3)
            if s['out_face'] == 'E': ax.plot([W, W], s.get("out_window_um",[0,0]), c=cols.get(s['name'], 'k'), lw=5)
            if s['in_face'] == 'E': ax.plot([W, W], s.get("in_window_um",[0,0]), c=cols.get(s['name'], 'k'), lw=5)
        x2 = max(h['origin_um'][0] + h['outline_um'][0] for h in t['hard_cores'])
        ax.set_aspect('equal'); ax.set_title(f"{p.split('/')[-1]}{' zoom y300-900' if zoom else ''}: E escape {W - x2:.3f} um")
        if zoom: ax.set_xlim(zoom[0], zoom[1]); ax.set_ylim(zoom[2], zoom[3]); ax.annotate('', (W, 600), (x2, 600), arrowprops=dict(arrowstyle='<->'))
        else: ax.set_xlim(-10, W + 10); ax.set_ylim(-10, H + 10)
for n, c in cols.items(): axs[0].scatter([], [], c=c, label=n)
axs[0].legend(loc='upper right', fontsize=7, markerscale=4)
plt.tight_layout(); plt.savefig(out, dpi=110)
