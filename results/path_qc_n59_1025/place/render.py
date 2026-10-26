"""PATH-QC-N59 render: native59 partition with the 8 regenerated writer SRAMs (16 lane enables), their read / write
pin faces, the exact FT bit sites (ft_sites.py, 21 slots) and the bus face windows.  Input native59_type.json."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
HERE = Path(__file__).resolve().parent
t = json.loads((HERE / 'native59_type.json').read_text())
w, h = t['outline_um']
fig, ax = plt.subplots(figsize=(13, 9), dpi=150)
ax.add_patch(Rectangle((0, 0), w, h, fill=False, lw=2))
cols = plt.cm.tab20.colors
for k, s in enumerate(t['ft_slots']):
    cw, ch = s['bit_site_cell_um']
    for stage in s.get('bit_sites_um', []):
        for x, y in stage:
            ax.add_patch(Rectangle((x, y), cw, ch, color=cols[k % 20], lw=0))
    xs = [x for st in s.get('bit_sites_um', []) for x, _ in st]
    ys = [y for st in s.get('bit_sites_um', []) for _, y in st]
    if xs:
        ax.text(max(xs) + 2, sum(ys) / len(ys), f"{s['name'][:18]} w{s['width']}", fontsize=4.5, color=cols[k % 20])
for c in t['contents']:
    if c.get('module') != 'ot_sram_1r1w_32x512_m1':
        continue
    x, y = c['origin_um']; mw, mh = c['outline_um']; i = c['inst'].split('g_writer[')[1].split(']')[0]
    ax.add_patch(Rectangle((x, y), mw, mh, facecolor='#c4d8ed', edgecolor='#31577c', lw=1.2))
    ax.add_patch(Rectangle((x - 8.64, y - 8.64), mw + 17.28, mh + 17.28, fill=False, ls=':', edgecolor='#31577c', lw=.6))
    rd = x + mw if c['orient'] == 'MY' else x          # master read face LEFT; MY mirrors it to the right
    wr = x if c['orient'] == 'MY' else x + mw
    ax.plot([rd, rd], [y + 1.4, y + 1.4 + 519 * 0.096], color='#d64f27', lw=3)
    ax.plot([wr, wr], [y + 0.8, y + 0.8 + 534 * 0.096], color='#269b67', lw=3)
    ax.text(x + mw / 2, y + mh / 2, f"bank {i} {c['orient']}\n32 x 512, 16 lane WE\n{mw:.2f} x {mh:.2f}", ha='center',
            va='center', fontsize=7)
for b in t['buses']:
    if 'face' not in b:
        continue
    lo, hi = b['window_um']; f = b['face']
    p = ([0, 0], [lo, hi]) if f == 'W' else ([w, w], [lo, hi]) if f == 'E' else ([lo, hi], [0, 0]) if f == 'S' else ([lo, hi], [h, h])
    ax.plot(*p, color='#1f77b4' if b['dir'] == 'in' else '#8d52a5', lw=4, solid_capstyle='butt')
cx, cy = t['clock']['tap_um']
ax.scatter([cx], [cy], marker='+', s=200, c='black', zorder=5); ax.text(cx + 5, cy + 5, 'clock tap', fontsize=7)
ax.plot([], [], color='#d64f27', lw=3, label='read face (clk, r_ce, r_addr, rd_out[511:0]) -> corridor')
ax.plot([], [], color='#269b67', lw=3, label='write face (w_ce, w_addr, 16 x {wd[32], we}) -> outer channel')
ax.plot([], [], color='#1f77b4', lw=4, label='bus window in'); ax.plot([], [], color='#8d52a5', lw=4, label='bus window out')
ax.plot([], [], ls=':', color='#31577c', label='8.64-um macro halo (FT cells: 0 inside)')
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.06), ncol=3, fontsize=7)
ax.set(xlim=(-20, w + 20), ylim=(-20, h + 20), aspect='equal', xlabel='um', ylabel='um',
       title='native59 (777.6 x 518.4): 8 writer SRAMs regenerated with 16 lane write enables (167.40 x 52.92, -30.5%)\n'
             'left col MY / right col R0, origins lattice + 0.012 um (8424/8424 pins on M4/M5 tracks); '
             '21 FT slots exact sites, 0 cells in macros/halos; PATH-QC-N59 10-25')
ax.title.set_fontsize(9); ax.grid(alpha=.15); fig.tight_layout(); fig.savefig(HERE / 'native59_n59_1025.png')
print('wrote', HERE / 'native59_n59_1025.png')
