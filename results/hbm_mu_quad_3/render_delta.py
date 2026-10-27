#!/usr/bin/env python3
"""render_delta.py PLAN_BEFORE PLAN_AFTER OUT.png: root tail engines (rest/sk resize, generated-clock arrows) and the
TKM corridor clock buffers (before red x, after green o) of the HBM-MU-QUAD-3 delta."""
import json, sys
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
A = json.load(open(sys.argv[1] + '/die_plan.json'))['partition_types']['root']
B = json.load(open(sys.argv[2] + '/die_plan.json'))['partition_types']['root']
fig, ax = plt.subplots(1, 2, figsize=(16, 8))
for a, (T, ttl) in zip(ax, ((A, 'before'), (B, 'after'))):
    for h in T['hard_cores']:
        x, y = h['origin_um']; w, hh = h['outline_um']
        if x > 1700 or y > 3600 or y + hh < 380: continue
        c = 'tab:orange' if 'tail' in h['inst'] else ('tab:blue' if 'tkm' in h['inst'] else '0.8')
        a.add_patch(Rectangle((x, y), w, hh, fc=c, ec='k', lw=0.5, alpha=0.6))
        if 'tail' in h['inst']: a.text(x + 4, y + 8, h['inst'].replace('u_hc_eng_', ''), fontsize=6, rotation=90)
    for b in T['clock'].get('branch_buffers', []):
        if 'tkmclk' in b['name']:
            a.plot(*b['xy'], 'gx' if ttl == 'after' else 'rx', ms=8)
            for d in b['drives']:
                tp = next(t for t in T['clock']['taps'] if t['name'] == d)
                a.plot([b['xy'][0], b['xy'][0], tp['xy'][0]], [b['xy'][1], tp['xy'][1], tp['xy'][1]], 'g-' if ttl == 'after' else 'r-', lw=0.8)
    tapn = {t['name'] for t in T['clock']['taps']}
    for t in T['clock']['taps']:
        if 'tail' in t['name']: a.plot(*t['xy'], 'k^', ms=5)
    a.set_xlim(150, 1700); a.set_ylim(380, 3600); a.set_aspect('equal'); a.set_title(f'root {ttl}: tail engines + TKM corridor clock buffers')
    if ttl == 'after':
        for N in (0, 1):
            r = next(h for h in T['hard_cores'] if h['inst'] == f'u_hc_eng_tail{N}_rest')
            for s in ('sk_step0', 'sk_steady'):
                k = next(h for h in T['hard_cores'] if h['inst'] == f'u_hc_eng_tail{N}_{s}')
                a.annotate('', xy=(k['origin_um'][0] + 20, k['origin_um'][1] + k['outline_um'][1] / 2),
                           xytext=(r['origin_um'][0] + 3, r['origin_um'][1] + r['outline_um'][1]),
                           arrowprops=dict(arrowstyle='->', color='m', lw=1))
        a.text(160, 3500, 'magenta: div-7 generated clock rest.sk_clk -> sk.clk (sk die taps removed)', fontsize=8, color='m')
plt.tight_layout(); plt.savefig(sys.argv[3], dpi=110)
