#!/usr/bin/env python3
"""Plot committed PVM endpoint constraints; model only, never a layout."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
ROOT=Path(__file__).resolve().parents[2]
def main():
 d=ROOT/'results/arch/hbm_pvm_safe2_1019/hop_model'
 m=json.loads((ROOT/'results/arch/hbm_pvm_safe2_1019/mirror_geometry_mapped/model.json').read_text())
 fig,ax=plt.subplots(figsize=(10,9))
 ax.add_patch(Rectangle((0,0),302.4,302.4,fill=False,lw=2))
 x0,y0,x1,y1=m['std_band_um']
 ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor='#dcecf1',edgecolor='#37738b',label='Only legal std-cell band; actual area fill42.63%'))
 ax.add_patch(Rectangle((43.2,43.2),171.288,153.912,facecolor='#d8d4bf',edgecolor='#6b6652',label='Complete calibrated SRAM R180'))
 ax.add_patch(Rectangle((86.4,230.04),172.8,17.28,facecolor='#efb46b',edgecolor='#ab6515',label='Actual internal macro cone8437cells;44.30% region fill'))
 ax.plot([86.4,172.8],[229.5,229.5],lw=3,c='#a43f40',label='546 exact-value west-side constant ties;51.19% region fill')
 ax.plot([86.4,259.2],[302.4,302.4],lw=5,c='#674d99',label='Seven whole input port groups;522 actual boundary registers')
 ax.plot([43.212,259.2],[43.98,247.32],ls='--',c='#a43f40',alpha=.7,label='Illustrative worst-side endpoint span; bound385.152µm')
 x,y=m['clock_xy_um'];ax.scatter([x],[y],c='red',s=50,zorder=5)
 ax.annotate('Clock contact:32.898µm to legal driver band',xy=(x,y),xytext=(14,210),arrowprops={'arrowstyle':'->'},fontsize=9)
 ax.text(128.844,130,'64×512 calibrated SRAM\n171.288×153.912µm\n43.2 lattice origin / R180',ha='center',va='center')
 ax.text(151,279,'Other cells share the same full-width row band\nNo second band or power domain; IO flops remain at N face',ha='center',fontsize=9)
 ax.set(xlim=(-5,307.4),ylim=(-5,320),xlabel='x (µm)',ylabel='y (µm)',title='PVM source-derived placement constraints\nModel only: actual placement, nativeTT/FF, access and route detours OPEN')
 ax.set_aspect('equal');ax.legend(loc='lower right',fontsize=8);fig.tight_layout();fig.savefig(d/'geometry.png',dpi=160);plt.close(fig)
if __name__=='__main__':main()
