#!/usr/bin/env python3
"""Render proposed exact native StoreB and its MX parent endpoint context. No placement."""
import json
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
ROOT=Path(__file__).resolve().parents[2]
r=ROOT/'results/hbm_storeB_native_capsule_0136';a=json.loads((r/'storeB_GEN_capsule.json').read_text());W,H=a['outline_um'];fig,axs=plt.subplots(1,2,figsize=(15,6))
ax=axs[0];ax.add_patch(Rectangle((0,0),W,H,fc='white',ec='black'))
for i,m in enumerate(a['macro_candidates']):
 x,y=m['origin_um'];w,h=m['outline_um'];ax.add_patch(Rectangle((x-4.32,y-4.32),w+8.64,h+8.64,fc='#ffecdc',ec='#aaa',lw=.3));ax.add_patch(Rectangle((x,y),w,h,fc='#ddd',ec='#666',lw=.5));ax.text(x+w/2,y+h/2,str(i),ha='center',fontsize=7)
for layer in ('M4','M5'):
 ps=[p for p in a['pins']if p['layer']==layer];ax.scatter([p['x']for p in ps],[p['y']for p in ps],s=1,label=layer+' true-ABI pins',rasterized=True)
ps=[p for p in a['pins']if p['face']=='S'];ax.scatter([p['x']for p in ps],[p['y']for p in ps],s=8,c='green',label='cmd0_Q[895:576]',rasterized=True)
ax.text(W/2,452,'4,086 declared preopt soft FF\nSoft logic, clock and PG are unplaced',ha='center',fontsize=9);ax.legend(loc='center left',fontsize=7);ax.set_aspect('equal');ax.set_xlim(-10,W+10);ax.set_ylim(-18,H+12);ax.set_title('Compact native StoreB proposal: 760.32 × 483.84 µm\n32 true SRAM masters / 7,864 exact ABI bits')
ax=axs[1];ax.add_patch(Rectangle((0,0),1857.6,1572.48,fc='white',ec='black'));ax.add_patch(Rectangle((656.64,216),W,691.2,fc='none',ec='#999',ls='--',label='Allocated parent context, old height691.2'))
ax.add_patch(Rectangle((656.64,216),W,H,fc='#e0efff',ec='#14599a',label='Proposed compact native provider, MX'))
xs=[656.64+p['x']for p in ps];ys=[216+H-p['y']for p in ps];ax.scatter(xs,ys,s=6,c='green',label='localS → parentN native exports')
ax.plot([1857.6,1857.6],[647.648,924.8147],c='orange',lw=4,label='Original upper L730 paired window')
ax.annotate('Native output face → relay → E capture\nDirect horizontal lower bound 448–502 µm >405\nExact sourceFF/relay placement and cycles HELD',xy=(1400,700),xytext=(220,1150),arrowprops=dict(arrowstyle='->'),fontsize=9)
ax.text(360,120,'Parent pose shown is B113-local; source13 unchanged.\nNo old-provider ABI/source compatibility is assumed.',fontsize=8);ax.set_aspect('equal');ax.set_xlim(-30,1900);ax.set_ylim(-30,1630);ax.legend(loc='upper left',fontsize=7);ax.set_title('B113 MX placement context: source outputs face north\nCompact height removes207.36µm; no active parent adoption')
for ax in axs:ax.set_xlabel('x (µm)');ax.set_ylabel('y (µm)')
fig.suptitle('GEN-only source/model proposal — no StoreB SOURCE_EQ, PLACE, clock/reset/START or timing qualification',fontsize=12);fig.tight_layout();fig.savefig(r/'storeB_GEN_review.png',dpi=150)
