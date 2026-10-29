#!/usr/bin/env python3
import argparse,collections,json
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=argparse.ArgumentParser();p.add_argument('--constraints',required=True);p.add_argument('--placements',required=True);p.add_argument('--out',required=True);a=p.parse_args();g=json.load(open(a.constraints));x=json.load(open(a.placements));D=g['dbu'];cc=x['cells'];bins=collections.Counter((c['bbox_dbu'][0]//60000,c['bbox_dbu'][1]//60000) for c in cc);fig,axs=plt.subplots(2,2,figsize=(16,13));axs=list(axs.flat)
centers=[(None,None)]+[k for k,v in bins.most_common(3)]
for ax,(xx,yy) in zip(axs,centers):
 bounds=[0,0,g['die_dbu'][2],g['die_dbu'][3]] if xx is None else[xx*60000-10000,yy*60000-10000,xx*60000+70000,yy*60000+70000]
 def hit(r):return r[0]<bounds[2] and bounds[0]<r[2] and r[1]<bounds[3] and bounds[1]<r[3]
 def rect(r,col,edge=None,lw=.3):
  if hit(r):ax.add_patch(Rectangle((r[0]/D,r[1]/D),(r[2]-r[0])/D,(r[3]-r[1])/D,facecolor=col,edgecolor=edge,lw=lw))
 if xx is None:
  for h in g['hard_forbidden']:rect(h[1:],'#dddddd')
 else:
  for o in g['actual_lower_OBS']:
   if o[1]=='M1':rect(o[2:],'#dddddd')
  for h in g['hard_forbidden']:rect(h[1:],'none','red')
 for c in g['existing_cells']:rect(c[2:],'green')
 if xx is None:ax.scatter([(c['bbox_dbu'][0]+c['bbox_dbu'][2])/2/D for c in cc],[(c['bbox_dbu'][1]+c['bbox_dbu'][3])/2/D for c in cc],s=.5,c='#2255cc')
 else:
  for c in cc:rect(c['bbox_dbu'],'#2255cc' if c['sequential'] else '#ee8800')
 ax.set_xlim(bounds[0]/D,bounds[2]/D);ax.set_ylim(bounds[1]/D,bounds[3]/D);ax.set_aspect('equal');ax.set_xlabel('um');ax.set_ylabel('um');ax.set_title('Whole die: provider cells and hard cores' if xx is None else f'Dense provider window {xx*60},{yy*60} um')
fig.suptitle('KV event27f: actual packed clock (green), provider FF (blue), comb (orange), immutable M1 OBS (grey)');plt.tight_layout();plt.savefig(a.out,dpi=110)
