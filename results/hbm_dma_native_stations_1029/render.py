#!/usr/bin/env python3
"""Render actual DMA station-center preparation against every retained core halo."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

HERE = Path(__file__).resolve().parent
j = json.loads((HERE/'core_rects.json').read_text())
fig, ax = plt.subplots(figsize=(16, 8.6), dpi=150)
for name, x0, y0, x1, y1 in j['rects']:
    special = name == 'u_hb_dbk_Q__q1' or name in {f'u_vmb_Q{k}' for k in range(8)}
    ax.add_patch(Rectangle((x0, y0), x1-x0, y1-y0,
                           facecolor='#ffc785' if special else '#ebedf0',
                           edgecolor='#7e8088', linewidth=0.5))
    ax.add_patch(Rectangle((x0-4.32, y0-4.32), x1-x0+8.64, y1-y0+8.64,
                           fill=False, edgecolor='#c0c3c8', linewidth=0.3))
    if special:
        ax.text((x0+x1)/2, (y0+y1)/2, name.replace('u_', ''), fontsize=6, ha='center')
colors = plt.get_cmap('tab10')
for f in sorted((HERE/'geometry').glob('bank*.json')):
    row = json.loads(f.read_text())
    if row['verdict'] != 'PASS':
        continue
    color = colors(row['bank'])
    pts = row['regs_um']
    x, y = zip(*pts)
    ax.plot(x, y, color=color, linestyle='-' if row['kind']=='request' else '--',
            linewidth=1.1, alpha=0.9, label=f"bank{row['bank']} {row['kind']} {row['stations']} stages")
    ax.scatter(x, y, c=[color], s=8, zorder=4)
    for side in ('src', 'dst'):
        xy = [p[side]['xy_um'] for p in row['endpoint_pin_pairs']]
        ax.scatter([p[0] for p in xy], [p[1] for p in xy], c=[color], s=1, alpha=0.4)
ax.set_xlim(0, j['outline_um'][0])
ax.set_ylim(0, j['outline_um'][1])
ax.set_aspect('equal')
ax.set_xlabel('NW hub type x (um)')
ax.set_ylabel('NW hub type y (um)')
ax.set_title('Actual DMA edges: 17-bit requests / 257-bit returns; station-center preparation\n'
             '16/16 paths, all-bit hop max362.88um, 4.32um core halos; FF body packing/RTL/timing NOT RUN')
ax.legend(fontsize=6, loc='upper left', bbox_to_anchor=(1.01, 1), frameon=False)
fig.tight_layout()
fig.savefig(HERE/'native_dma_stations.png')
