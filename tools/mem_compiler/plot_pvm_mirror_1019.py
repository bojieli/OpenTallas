#!/usr/bin/env python3
"""Draw the exact model packet; never labels it a physical layout."""
import json
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
ROOT=Path(__file__).resolve().parents[2]
def main():
 d=ROOT/'results/arch/hbm_pvm_safe2_1019/mirror_geometry_mapped';m=json.loads((d/'model.json').read_text());fig,ax=plt.subplots(figsize=(8,8))
 ax.add_patch(Rectangle((0,0),302.4,302.4,fill=False,lw=2))
 x0,y0,x1,y1=m['std_band_um'];ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor='#badce8',edgecolor='#37738b',label='Single legal standard-cell band'))
 ax.add_patch(Rectangle((43.2,43.2),171.288,153.912,facecolor='#d8d4bf',edgecolor='#6b6652',label='Complete SRAM rotated R180'))
 x,y=m['clock_xy_um'];ax.scatter([x],[y],c='red',s=60,zorder=5,label='SRAM clock contact')
 ax.annotate(f"{m['clock_gap_to_band_um']:.3f} µm to legal driver band",xy=(x,y0),xytext=(x-155,211),arrowprops={'arrowstyle':'->'},fontsize=9)
 ax.text(128.844,120,'64 × 512 SRAM\nR180\n171.288 × 153.912 µm',ha='center',va='center')
 ax.text(151.2,264,f"Actual mapped standard cells: {m['std_area_um2']:,.3f} µm²\n{100*m['std_band_fill']:.2f}% of actual core-row band\nAll source driver loads ≤25 after tie repair\nCTS/native timing remain unqualified",ha='center',va='center',fontsize=9)
 ax.scatter([150],[302.4],c='purple',marker='v',s=60,label='Tile clock contact')
 ax.set(xlim=(-5,307.4),ylim=(-5,325),xlabel='x (µm)',ylabel='y (µm)',title='PVM mirror successor: actual mapped area budget\nModel geometry; not a placed or routed layout');ax.set_aspect('equal');ax.legend(loc='lower right',fontsize=8);fig.tight_layout();fig.savefig(d/'geometry.png',dpi=160);plt.close(fig)
if __name__=='__main__':main()
