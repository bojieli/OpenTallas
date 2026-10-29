#!/usr/bin/env python3
"""Minimal actual-pin geometry diagnosis of the rejected centroid turn."""
import json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[3]);import schema as S
from gen_phys import type_pins
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=S.Plan(json.loads((Path(sys.argv[1])/'die_plan.json').read_text()));tn=p.parts['NE_b101']['type'];t=p.types[tn];W,H=t['outline_um'];slot=next(s for s in t['ft_slots'] if s['name']=='L12x1');pins={(b,i):(x,y) for b,i,_,x,y,_ in type_pins(p,tn)};a=np.array([pins['L12x1_i',i] for i in range(slot['width']+1)]);b=np.array([pins['L12x1_o',i] for i in range(slot['width']+1)]);corner=np.array([b[:,0].mean(),a[:,1].mean()]);pre=corner+np.column_stack([np.zeros(len(a)),a[:,1]-a[:,1].mean()]);post=corner+np.column_stack([b[:,0]-b[:,0].mean(),np.zeros(len(a))]);jump=np.abs(pre-post).sum(axis=1);idx=np.linspace(0,len(a)-1,19).astype(int)
fig,axes=plt.subplots(1,2,figsize=(10,10),sharex=True,sharey=True)
for ax in axes:
 for name,(x0,y0,x1,y1) in S.placed_macro_boxes(t,halo=0).items():ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor='#dddddd',edgecolor='#555555',linewidth=.5))
 ax.set_xlim(-10,W+10);ax.set_ylim(-10,H+20);ax.set_aspect('equal');ax.set_xlabel('local x (um)');ax.grid(alpha=.15)
for i in idx:
 old=np.stack([a[i],pre[i],post[i],b[i]]);new=np.stack([a[i],[b[i,0],a[i,1]],b[i]])
 axes[0].plot(old[:,0],old[:,1],color='#b22222',alpha=.5,lw=.65)
 axes[1].plot(new[:,0],new[:,1],alpha=.65,lw=.7)
if len(sys.argv)>4:
 allocated=json.loads((Path(sys.argv[4])/'die_plan.json').read_text());part=next(p for p in allocated['partitions'] if p['name']=='NE_b101');tt=allocated['partition_types'][part['type']];ss=next(s for s in tt['ft_slots'] if s['name']=='L12x1')
 for stage in ss.get('bit_sites_um',[]):
  xy=np.array(stage)+np.array([.702,.135]);axes[1].scatter(xy[:,0],xy[:,1],s=.35,c='navy',alpha=.5)
for ax in axes:ax.scatter(a[idx,0],a[idx,1],s=9,c='navy');ax.scatter(b[idx,0],b[idx,1],s=9,c='navy')
axes[0].set_title(f'Rejected centroid corner\nmax discontinuous bit jump {jump.max():.2f} um')
axes[1].set_title('Continuous own-bit Manhattan corners\n' + (str(ss['stations'])+' stages; actual FF homes shown' if len(sys.argv)>4 else 'station placement and paired-hop gate remain required'))
axes[0].set_ylabel('local y (um)');fig.suptitle(f'NE_b101 / L12x1: {slot["width"]} data bits + epoch, actual pin coordinates\nM6/M7 signal wires may cross M5 cores; all FF homes must stay in free rows',fontsize=11);fig.tight_layout();fig.savefig(sys.argv[2],dpi=140);plt.close(fig)
