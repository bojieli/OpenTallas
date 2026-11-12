"""type render: hard cores (opsa_group0 highlighted), ft slot station chains, before | after. usage: PLAN_A PLAN_B TYPE OUT"""
import json, sys
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
a, b, tn, out = sys.argv[1:5]
fig, axs = plt.subplots(1, 2, figsize=(26, 12), facecolor='white')
for ax, (pl, ttl) in zip(axs, ((a, 'BEFORE base0 fc8d47cd26a1'), (b, 'AFTER opsa_group0 form B e4ae695c7698'))):
    t = json.load(open(pl))['partition_types'][tn]; W, H = t['outline_um']
    ax.add_patch(Rectangle((0, 0), W, H, fc='#f7f7f7', ec='k'))
    for h in t['hard_cores']:
        g0 = h['module'] == 'ot_hgi_sfu_opsa_group0'
        ax.add_patch(Rectangle(h['origin_um'], *h['outline_um'], fc='#f4a261' if g0 else '#bbbbbb', ec='k', lw=0.4))
        ax.text(h['origin_um'][0] + h['outline_um'][0] / 2, h['origin_um'][1] + h['outline_um'][1] / 2,
                h['inst'].replace('u_sfucore_Q_', ''), fontsize=7, ha='center', va='center')
    for s in t['ft_slots']:
        r = s.get('regs_um', [])
        if not r: continue
        hot = s['width'] >= 300
        ax.plot([p[0] for p in r], [p[1] for p in r], '-o', ms=3 if hot else 1.5, lw=1.4 if hot else 0.5,
                color='tab:blue' if hot else 'tab:green', alpha=0.9 if hot else 0.5)
        if hot: ax.text(r[-1][0], r[-1][1], f"{s['name']} {s['width']}b", fontsize=6, color='tab:blue')
    ax.set_xlim(-20, W + 20); ax.set_ylim(-20, H + 20); ax.set_aspect('equal'); ax.set_title(f'{tn}  {ttl}')
plt.tight_layout(); plt.savefig(out, dpi=100)
