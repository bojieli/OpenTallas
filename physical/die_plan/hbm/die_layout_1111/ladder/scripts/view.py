"""DIE-LAYOUT-HBM ladder: before/after view of the NE/NW bank blocks (partitions, hard cores, FT slot routes)."""
import json, sys
sys.path.insert(0, sys.argv[1])
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import schema as S
plans = [(sys.argv[2], 'BEFORE ' + sys.argv[4]), (sys.argv[3], 'AFTER ' + sys.argv[5])]
out = sys.argv[6]
fig, ax = plt.subplots(2, 2, figsize=(22, 20), facecolor='white')
for col, (pl, title) in enumerate(plans):
    P = S.Plan(json.load(open(pl)))
    for row, side in enumerate(('NE', 'NW')):
        a = ax[row][col]
        hub = P.rect(f'{side}_hub')
        bx = [P.rect(n) for n in P.parts if n.startswith(side + '_b0')]
        x0 = min(r[0] for r in bx) - 700; x1 = max(r[2] for r in bx) + 700
        y0 = min(r[1] for r in bx) - 500; y1 = max(r[3] for r in bx) + 500
        for n in P.parts:
            r = P.rect(n)
            if r[2] < x0 or r[0] > x1 or r[3] < y0 or r[1] > y1:
                continue
            isb = '_b0' in n
            a.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc='#dbe9ff' if isb else '#f0f0f0',
                                  ec='k', lw=1.2 if isb else 0.5))
            a.text((max(r[0], x0) + min(r[2], x1)) / 2, (max(r[1], y0) + min(r[3], y1)) / 2, n.split('_', 1)[1],
                   ha='center', va='center', fontsize=11 if isb else 7, color='#003' if isb else '#666', zorder=5)
            if not isb:
                continue
            for h in P.ptype(n).get('hard_cores', []):
                c0 = P.to_die(n, tuple(h['origin_um']))
                c1 = P.to_die(n, (h['origin_um'][0] + h['outline_um'][0], h['origin_um'][1] + h['outline_um'][1]))
                a.add_patch(Rectangle((min(c0[0], c1[0]), min(c0[1], c1[1])), abs(c1[0] - c0[0]), abs(c1[1] - c0[1]),
                                      fc='#9ab', ec='none', alpha=0.6))
            for s in P.ptype(n).get('ft_slots', []):
                fi, wi, _, _ = P.geom_to_die(n, (s['in_face'], s['in_window_um'], s['in_layers'], 'lsb_low'))
                fo, wo, _, _ = P.geom_to_die(n, (s['out_face'], s['out_window_um'], s['out_layers'], 'lsb_low'))
                def pt(f, w):
                    c = (w[0] + w[1]) / 2
                    return {'E': (r[2], c), 'W': (r[0], c), 'N': (c, r[3]), 'S': (c, r[1])}[f]
                p, q = pt(fi, wi), pt(fo, wo)
                w = s['width']
                a.plot([p[0], q[0], q[0]] if fi in 'EW' else [p[0], p[0], q[0]],
                       [p[1], p[1], q[1]] if fi in 'EW' else [p[1], q[1], q[1]],
                       color='#c00' if w >= 1000 else ('#e80' if w >= 300 else '#08a'), lw=0.4 + w / 800, alpha=0.7)
        a.set_xlim(x0, x1); a.set_ylim(y0, y1); a.set_aspect('equal')
        nsl = sum(len(P.ptype(n).get('ft_slots', [])) for n in P.parts if n.startswith(side + '_b0'))
        nst = sum(int(s.get('stations', 1)) * s['width'] for n in P.parts if n.startswith(side + '_b0')
                  for s in P.ptype(n).get('ft_slots', []))
        a.set_title(f'{title}  {side} bank block: {nsl} FT slots in banks, {nst/1000:.0f}k station flops\n'
                    f'slot routes red >=1000 b, orange >=300 b, blue <300 b; grey = hard cores', fontsize=11)
plt.tight_layout(); plt.savefig(out, dpi=80)
print('wrote', out)
