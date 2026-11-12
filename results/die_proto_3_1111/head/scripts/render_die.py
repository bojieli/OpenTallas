import json, gzip, sys, collections
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
inp, out, title = sys.argv[1:4]
d = json.load(gzip.open(inp)); B = d['bin']; W, H = d['die']
nx, ny = int(W // B) + 1, int(H // B) + 1
fig, ax = plt.subplots(1, 3, figsize=(30, 10.5))
# (1) guide area density all signal layers M4-M7 (fraction of bin area, summed over layers)
for i, (layers, lab) in enumerate([(('M4', 'M5', 'M6', 'M7'), 'GRT guide area M4-M7 / bin area'), (('M8', 'M9'), 'GRT guide area M8-M9 (clock) / bin area')]):
    g = np.zeros((ny, nx))
    for L, x, y, a in d['guide']:
        if L in layers and 0 <= x < nx and 0 <= y < ny: g[y, x] += a / (B * B)
    im = ax[i].imshow(g, origin='lower', extent=[0, W, 0, H], cmap='magma', vmax=max(np.percentile(g[g > 0], 99.5), 1e-3) if (g > 0).any() else 1)
    plt.colorbar(im, ax=ax[i], fraction=0.04); ax[i].set_title(lab)
ty = sorted({p[1] for p in d['parts']}); cmap = plt.get_cmap('tab20', len(ty))
for a in ax:
    for n, t, x, y, w, h in d['parts']:
        a.add_patch(Rectangle((x, y), w, h, fill=False, lw=0.4, ec='cyan' if a is not ax[2] else cmap(ty.index(t))))
    a.set_xlim(0, W); a.set_ylim(0, H); a.set_aspect('equal')
t = np.array([[r[0], r[1], r[2]] for r in d['taps'] if r[2] is not None])
sc = ax[2].scatter(t[:, 0], t[:, 1], c=t[:, 2], s=2, cmap='turbo')
plt.colorbar(sc, ax=ax[2], fraction=0.04, label='tap late arrival TT (ps)')
ax[2].set_title('die clock taps (TT late, routed RC) over partitions')
for n, tt, x, y, w, h in d['parts']:
    if w * h > 6e5: ax[2].text(x + w / 2, y + h / 2, tt.replace('hd_', ''), fontsize=5, ha='center', va='center')
fig.suptitle(title); fig.tight_layout(); fig.savefig(out, dpi=110)
print('ok', out)
