import json, sys, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P = json.load(open(sys.argv[1])); T = P['partition_types']; out = sys.argv[2]
ys = float(sys.argv[3]); dH = 794.88
W, H = P['die']['outline_um']
fig, axs = plt.subplots(1, 2, figsize=(22, 11), gridspec_kw=dict(width_ratios=[1.6, 1]))
LANES = ('L28', 'L36', 'L106', 'L125', 'L9', 'L63')
COL = dict(L28='r', L36='m', L106='b', L125='c', L9='g', L63='orange')
def todie(p, q):
    t = T[p['type']]; w = t['outline_um'][0]; ox, oy = p['origin_um']
    x = w - q[0] if p.get('orient') == 'MY' else q[0]
    return ox + x, oy + q[1]
for ax, (x0, x1, y0, y1, title) in zip(axs, [(-100, W + 100, -100, H + 100, 'planU3 die (spanning growth +794.88 at y=%.2f)' % ys),
                                             (-50, 5300, 5800, 12300, 'NW hub-row columns zoom: grown strip (yellow) + restationed ft (dots)')]):
    for p in P['partitions']:
        t = T[p['type']]; w, h = t['outline_um']; ox, oy = p['origin_um']
        fc = '#dfe8f5' if 'hub' in p['name'] else '#eef0f2'
        ax.add_patch(Rectangle((ox, oy), w, h, fc=fc, ec='k', lw=.6))
        if ax is axs[1] or w * h > 4e6:
            ax.text(ox + w / 2, oy + h / 2, p['name'], fontsize=6 if ax is axs[0] else 7, ha='center', va='center')
        if oy < ys < oy + h:
            ax.add_patch(Rectangle((ox, ys), w, dH, fc='#ffe08a', ec='none', alpha=.6))
        if ax is axs[1]:
            for hc in t.get('hard_cores', []):
                if hc.get('origin_um') and hc.get('outline_um'):
                    a = todie(p, hc['origin_um']); b = todie(p, [hc['origin_um'][0] + hc['outline_um'][0], hc['origin_um'][1] + hc['outline_um'][1]])
                    ax.add_patch(Rectangle((min(a[0], b[0]), a[1]), abs(b[0] - a[0]), b[1] - a[1], fc='#c9ccd3', ec='#555', lw=.3))
        for f in t.get('ft_slots', []):
            ln = f['name'].split('x')[0].split('_')[0].rstrip('m')
            if ln in LANES:
                pts = [todie(p, q) for q in f.get('regs_um', [])]
                ax.plot([q[0] for q in pts], [q[1] for q in pts], '.-', color=COL[ln], ms=4, lw=.8)
    ax.axhline(ys, color='orange', ls=':', lw=.8); ax.axhline(ys + dH, color='orange', ls=':', lw=.8)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.set_title(title, fontsize=9)
for ln, c in COL.items():
    axs[1].plot([], [], '.-', color=c, label=ln)
axs[1].legend(fontsize=7, loc='lower right')
plt.tight_layout(); plt.savefig(out, dpi=100)
