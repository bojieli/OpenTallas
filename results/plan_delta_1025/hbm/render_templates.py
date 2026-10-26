"""render each PLAN-DELTA/HBM pin template (core frame, pins by layer, ID strap pins highlighted)"""
import json, sys, os, re
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
here = os.path.dirname(os.path.abspath(__file__)); pdir = os.path.join(here, '../../../physical/die_plan/hbm')
G = json.load(open(os.path.join(here, 'delta_groups.json')))['groups']
out = sys.argv[1]
fig, axs = plt.subplots(1, len(G), figsize=(5 * len(G), 5.6))
for ax, (g, v) in zip(axs, sorted(G.items())):
    P = json.load(open(os.path.join(pdir, v['pins_file'])))
    w, h = map(float, re.search(r'__([\d.]+)x([\d.]+)\.json$', v['pins_file']).groups())
    ax.add_patch(plt.Rectangle((0, 0), w, h, fill=False, lw=1.2))
    for lay, c in (('M4', 'tab:blue'), ('M5', 'tab:orange'), ('M6', 'tab:green'), ('M7', 'tab:purple')):
        q = [p for p in P if p['layer'] == lay and not any(p['name'].startswith(s) for s in v['straps'])]
        if q: ax.scatter([p['x'] for p in q], [p['y'] for p in q], s=3, c=c, label=f'{lay} {len(q)}')
    st = [p for p in P if any(p['name'].startswith(s) for s in v['straps'])]
    if st:
        ax.scatter([p['x'] for p in st], [p['y'] for p in st], s=60, marker='x', c='red', label=f'ID strap {len(st)}')
    orients = sorted({m['orient'] for m in v['members']})
    ax.set_title(f"{g.split(':')[-2] if g.startswith('single') else g}\n{v['module']}\n{len(v['members'])} entries, orient {orients}, "
                 f"max disp {max(m['max'] for m in v['members']):.0f} um", fontsize=8)
    ax.set_aspect('equal'); ax.set_xlim(-15, w + 15); ax.set_ylim(-15, h + 15); ax.legend(fontsize=6, loc='center')
plt.tight_layout(); plt.savefig(out, dpi=110)
