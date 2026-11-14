"""QC-S28-D before/after render of the bc column spine per type (plan geometry + placed dump before, plan sites after)."""
import json, sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

D = Path(sys.argv[1]); OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
hops = {}
for ln in open(D / 'hops_s28d.tsv').read().splitlines()[1:]:
    t, bus, h, a, b, L, over, _ = (ln.split('\t') + [''] * 8)[:8]
    hops.setdefault(t, []).append((bus, a, b, float(L)))
COLS = ['#1f77b4', '#9467bd', '#17becf', '#8c564b']


def base(ax, sp, title):
    W, H = sp['outline']
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, ec='k', lw=1))
    for c in sp['cores']:
        a, b, c2, d, inst, o = c
        nk = (c2 - a) > 300
        ax.add_patch(Rectangle((a, b), c2 - a, d - b, fc='#f3d9b1' if nk else '#cccccc', ec='#996633', lw=0.6))
        ax.text((a + c2) / 2, (b + d) / 2, f'{inst}\n{o}', ha='center', va='center', fontsize=7)
    for k, r in sp['bands'].items():
        if r:
            ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc='#ffb3b3', ec='r', lw=0.4, alpha=0.7))
            ax.text(r[0], r[3] + 6, k, fontsize=5, color='r')
    ax.set_xlim(-20, W + 20); ax.set_ylim(-20, H + 20); ax.set_aspect('equal'); ax.set_title(title, fontsize=8)
    ax.tick_params(labelsize=6)


for spf in sorted(D.glob('spine_*.json')):
    sp = json.load(open(spf)); tn = sp['type']
    bef = json.load(open(D / f'{tn}.json')) if (D / f'{tn}.json').exists() else None
    fig, axs = plt.subplots(1, 2, figsize=(11, 11.5))
    # BEFORE
    base(axs[0], sp, f'{tn} BEFORE (placed dump, every 8th bit)\nbc column flops: bin / station b_q (o) t_q (^) / d-chain (.) / u_pc tap (x)')
    if bef:
        for ci, col in enumerate(sp['columns']):
            cc = COLS[ci % 4]; chain = [s['st'] for s in col['stations']]
            for k, v in bef.items():
                mine = (k.startswith('u_bin_' + col['bus'])) or any(k.startswith(s + '#') or (s[2:] in k and k.startswith('u_d')) for s in chain) \
                    or any(k == f'u_pc_nk_u_t_{s[-3]}_{s[-1]}_tap' for s in chain)
                if not mine:
                    continue
                xs, ys = zip(*v)
                mk = 'x' if k.startswith('u_pc') else '^' if k.endswith('#T') else 'o' if k.endswith('#B') or k.startswith('u_bin') else '.'
                axs[0].scatter(xs, ys, s=6, c=cc, marker=mk, alpha=0.6)
            axs[0].text(10, sp['outline'][1] - 40 - 30 * ci, f"{col['bus']}: before max hop see table", fontsize=6, color=cc)
    else:
        axs[0].text(100, 1200, 'no placed dump for this type\n(same RTL form as its sibling)', fontsize=9)
    # AFTER
    base(axs[1], sp, f'{tn} AFTER s28d spine (relay_sites, +0 cycles)\ngreen <=405, orange <=450, red >450 um (L1 geodesic)')
    hl = hops.get(tn, [])
    for ci, col in enumerate(sp['columns']):
        cc = COLS[ci % 4]
        n = col['nodes']
        groups = {g['group']: g['xy'] for g in col['groups']}
        for g, xy in groups.items():
            mk = '^' if g.endswith('#T') else 'o' if g.endswith('#B') or g.startswith('u_bin') else 's'
            axs[1].scatter([xy[0]], [xy[1]], s=28, c=cc, marker=mk, edgecolors='k', linewidths=0.4, zorder=5)
        # straight chords stage->stage coloured by planned geodesic hop
        seq = [('ring', col['in_point'])]
        seq.append(('bin', groups[f"u_bin_{col['bus']}"]))
        for k, s in enumerate(col['stations']):
            seq.append((s['st'] + '.b_q', s['b_q']))
            axs[1].plot([s['b_q'][0], s['t_q'][0]], [s['b_q'][1], s['t_q'][1]], c=cc, lw=0.6, ls=':')
            tp = s['tap']; tm = ((tp[0][0] + tp[1][0]) / 2, (tp[0][1] + tp[1][1]) / 2)
            Lt = max([h[3] for h in hl if h[0] == col['bus'] and h[1] == s['st'] + '.t_q'] or [0])
            axs[1].plot([s['t_q'][0], tm[0]], [s['t_q'][1], tm[1]], c='g' if Lt <= 405 else 'orange' if Lt <= 450 else 'r', lw=1.4)
            axs[1].scatter([tm[0]], [tm[1]], marker='x', c='k', s=30, zorder=6)
            for g, xy in groups.items():
                if g.startswith('u_d') and s['st'][2:] in g:
                    seq.append((g, xy))
        for (a, pa), (b, pb) in zip(seq, seq[1:]):
            axs[1].plot([pa[0], pb[0]], [pa[1], pb[1]], c=cc, lw=1.0, alpha=0.8)
        over = [h for h in hl if h[0] == col['bus'] and h[3] > 405]
        mx = max([h[3] for h in hl if h[0] == col['bus']] or [0])
        axs[1].text(10, sp['outline'][1] - 40 - 30 * ci, f"{col['bus']}: planned max hop {mx:.0f} um, {len(over)} hops >405", fontsize=6, color=cc)
    fig.tight_layout()
    fig.savefig(OUT / f'spine_{tn}.png', dpi=110); plt.close(fig)
    print('wrote', OUT / f'spine_{tn}.png')
