from pathlib import Path
import json
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import pg_regions as G
R=Path(__file__).parent;m=json.loads((R/'domain3/domains.json').read_text());W,H=m['die']['outline_um'];fig,axs=plt.subplots(1,2,figsize=(12,7),layout='constrained')
for j,ax in enumerate(axs):
 lim=[0,W,0,H]if j==0 else[765,790,195,220]
 ax.set(xlim=lim[:2],ylim=lim[2:],aspect='equal')
 for reg in G.regions(m['die']):
  a,b,c,d=reg['rect_um'];pwr=reg['nets'][0]
  for st in reg['grid']:
   horizontal=st['layer']=='M8';lo=b if horizontal else a;hi=d if horizontal else c;pitch=st['pitch_um']
   off=(st['offset_um']-lo)%pitch
   for bit in [0,1]:
    v=lo+off+bit*pitch/2
    while v<hi:
     if horizontal and lim[2]<=v<=lim[3]:ax.plot([a,c],[v,v],c='black'if bit==0 else'purple'if pwr=='VDDPHY'else'red',alpha=.35 if j==0 else .75,lw=.18 if j==0 else .6)
     if not horizontal and lim[0]<=v<=lim[1]:ax.plot([v,v],[b,d],c='black'if bit==0 else'purple'if pwr=='VDDPHY'else'red',alpha=.35 if j==0 else .75,lw=.18 if j==0 else .6)
     v+=pitch
 for r in m['die']['pg']['domains']:
  a,b,c,d=r['rect_um'];ax.add_patch(Rectangle((a,b),c-a,d-b,fill=False,ec='purple',lw=1.2,zorder=7))
 for n,x,y in m['bumps']:ax.scatter(x,y,c='purple'if n=='VDDPHY'else'red'if n=='VDD'else'black',marker='s',s=15,zorder=8)
 ax.set(xlabel='Window x (um)',ylabel='Window y (um)',title='Full PG window'if j==0 else'25um seam detail: every third ground rail lands')
fig.suptitle('PHY-local supply candidate; original bump sites, load power and core PG unchanged\nPurple=VDDPHY; red=core VDD; black=shared VSS; no clock/data routes in this coupon')
fig.savefig(R/'qc_pg_domain3_review.png',dpi=160)
