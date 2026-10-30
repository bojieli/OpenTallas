#!/usr/bin/env python3
"""View the candidate LP hard children, macro sites, storage bands and clock entries."""
import argparse
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

a=argparse.ArgumentParser();a.add_argument('plan');a.add_argument('out');x=a.parse_args()
p=json.load(open(x.plan));fig,axes=plt.subplots(2,2,figsize=(18,15))
for ax,(tn,t) in zip(axes.flat,[(n,t)for n,t in p['partition_types'].items()if '_LP__'in n]):
    W,H=t['outline_um'];ax.add_patch(Rectangle((0,0),W,H,fill=False,color='black'))
    for c in t['contents']:
        if not c.get('lef'):continue
        xx,y=c['origin_um'];w,h=c['outline_um']
        ax.add_patch(Rectangle((xx,y),w,h,facecolor='#9ba7b0',edgecolor='#4b5760',lw=.3))
    for c in t['hard_cores']:
        xx,y=c['origin_um'];dx,dy=c['track_offset_um'];w,h=c['outline_um']
        ax.add_patch(Rectangle((xx+dx,y+dy),w,h,facecolor='#dfaa55'if'lnland'in c['module']else'#6895be',edgecolor='black',lw=.8))
        ax.text(xx+w/2,y+h/2,c['inst'].split('.')[-1],ha='center',va='center',fontsize=8)
    for b in t['clock']['landing_contract']['bands'].values():
        xx,y,x1,y1=b['rect_um'];ax.add_patch(Rectangle((xx,y),x1-xx,y1-y,facecolor='#a5c76b',edgecolor='#5e792d',lw=.4))
    for q in t['clock']['taps']:
        xx,y=q['xy'];ax.plot(xx,y,'ro',ms=3)
    ax.axvspan(615.708,820.908,facecolor='#dfc8df',alpha=.25)
    ax.text(718,800,'FT STREET',rotation=90,ha='center',color='#835583',fontsize=10)
    ax.set_xlim(-20,W+20);ax.set_ylim(-20,H+20);ax.set_aspect('equal')
    ax.set_title(tn.replace('dsdv_slice_','')+' H2 candidate',fontsize=12);ax.set_xlabel('um');ax.set_ylabel('um')
fig.suptitle('S81 LP H2: 28 existing-module hard children / 42 clock entries; candidate, not physical sign-off',fontsize=15)
fig.tight_layout();fig.savefig(x.out,dpi=150)
