#!/usr/bin/env python3
"""Actual per-bit FT homes for a narrow partition construction review."""
import argparse,json,sys
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('allocated');ap.add_argument('part');ap.add_argument('image');ap.add_argument('--tools',required=True);a=ap.parse_args();sys.path.insert(0,a.tools);import schema as S
from gen_phys import type_pins
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=S.Plan(json.loads((Path(a.allocated)/'die_plan.json').read_text()));t=p.ptype(a.part);tn=p.parts[a.part]['type'];W,H=t['outline_um'];pins={(n,i):(x,y) for n,i,_,x,y,_ in type_pins(p,tn)};fig,ax=plt.subplots(figsize=(12,10));palette=plt.get_cmap('tab20');count=0
for name,(x0,y0,x1,y1) in S.placed_macro_boxes(t,halo=0).items():
 ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fc='#e5e5e5',ec='#555555',lw=.7));ax.text((x0+x1)/2,(y0+y1)/2,name.replace('u_','')[:28],ha='center',va='center',fontsize=5,clip_on=True)
slots=sorted(t.get('ft_slots',[]),key=lambda s:-s['width'])
for index,s in enumerate(slots):
 for stage in s.get('bit_sites_um',[]):
  q=np.array(stage)+np.array([.702,.135]);ax.scatter(q[:,0],q[:,1],s=1.1,color=palette(index%20),alpha=.7,linewidths=0);count+=len(q)
 if index<4:
  cloud=np.vstack(s.get('bit_sites_um',[[[0,0]]]))
  ax.scatter([],[],s=14,color=palette(index%20),label=s['name']+f' {s["width"]}b / {s["stations"]} stages')
s=slots[0];nb=s['width']+1
for bit in np.linspace(0,nb-1,13).astype(int):
 chain=np.array([pins[s['name']+'_i',bit],*[np.array(stage[bit])+[.702,.135] for stage in s['bit_sites_um']],pins[s['name']+'_o',bit]])
 ax.plot(chain[:,0],chain[:,1],lw=.35,c='#223344',alpha=.4)
ax.set_xlim(-15,W+15);ax.set_ylim(-15,H+15);ax.set_aspect('equal');ax.grid(alpha=.12);ax.set_xlabel('local x (um)');ax.set_ylabel('local y (um)');ax.set_title(a.part+f': {count:,} actual internal FT FF homes\nM5 hard cores gray; sampled r2r edges are planning connections, not routed wires');ax.legend(loc='upper right',fontsize=7);fig.tight_layout();fig.savefig(a.image,dpi=150);plt.close(fig)
