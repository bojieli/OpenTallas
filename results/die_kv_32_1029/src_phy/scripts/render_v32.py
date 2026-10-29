#!/usr/bin/env python3
"""DIE-KV-32-SRC review render: where the variant-A failures were (plan_off) and how the clean plan reaches PG there.
Zooms show M8 PG stripes (VDD red / VSS blue), M8 clock-leg reservations (BLOCK M8 0.40-um tall, black hatched),
new access M7 stems + VIA78 (dots) and M8 bridges (thick) of the clean plan, and std-cell rails of formerly failed groups (green)."""
import json,sys,collections
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plan,off,ovp,pgp,out=sys.argv[1:6];D=1000
P=json.load(open(plan+'/access_plan.json'));F=json.load(open(off+'/access_plan.json'))['failed']
pg=json.load(open(pgp));ov=json.load(open(ovp))
ck=[o[2:] for o in ov['obstructions'] if o[0]=='BLOCK' and o[1]=='M8' and o[5]-o[3]==400]
m8=[(n,[v*D for v in r]) for n,ly,*r in pg if ly=='M8']
fk={tuple(q['rail']) for q in F};byrail={tuple(q['rail']):q for q in P['paths']}
fig,aa=plt.subplots(2,2,figsize=(16,12),constrained_layout=True);ax=aa.flat[0]
col={'M9_bridge':'#7a3db8','M8_stripe':'#1a9a50'}
for how in col:
 pts=[((q['rail'][0]+q['rail'][2])/2/D,(q['rail'][1]+q['rail'][3])/2/D) for k in fk for q in [byrail.get(k)] if q and q['landing']==how]
 if pts:ax.scatter(*zip(*pts),s=1,color=col[how],label=f'formerly failed -> {how} ({len(pts):,})',rasterized=True)
left=[k for k in fk if k not in byrail]
if left:ax.scatter([(k[0]+k[2])/2/D for k in left],[(k[1]+k[3])/2/D for k in left],s=12,color='red',marker='x',label=f'still failed ({len(left)})')
ax.set_xlim(0,11076.48);ax.set_ylim(0,27043.2);ax.set_aspect('equal');ax.legend(loc='upper right',fontsize=8,markerscale=6)
ax.set_title(f"KV die: {len(F):,} variant-A failed groups; clean plan {len(P['paths']):,} groups / {len(P['failed'])} failed")
# zoom centres: first formerly-failed rail near a clock leg, one with none within 10.8 um, and one in a M8-stripe gap
cs=[]
for bk in ('clock_M8_reserve_within_1.4um','no_clock_M8_reserve_within_10.8um','clock_M8_reserve_within_5.4um'):
 q=next((q for q in F if q['clock_bucket']==bk),None)
 if q:cs.append((bk,(q['rail'][0]+q['rail'][2])/2,(q['rail'][1]+q['rail'][3])/2))
for a,(bk,cx,cy) in zip(list(aa.flat)[1:],cs):
 w=12000;x0,y0,x1,y1=cx-w,cy-w,cx+w,cy+w
 inb=lambda r:not(r[2]<x0 or r[0]>x1 or r[3]<y0 or r[1]>y1)
 for n,r in m8:
  if inb(r):a.add_patch(Rectangle((r[0]/D,r[1]/D),(r[2]-r[0])/D,(r[3]-r[1])/D,color='#e43b36' if n=='VDD' else '#2976bd',alpha=.45,lw=0))
 for r in ck:
  if inb(r):a.add_patch(Rectangle((r[0]/D,r[1]/D),(r[2]-r[0])/D,(r[3]-r[1])/D,facecolor='none',edgecolor='black',hatch='////',lw=.6))
 for q in P['paths']:
  x,y=q['stack']
  if not(x0<=x<=x1 and y0<=y<=y1):continue
  c='#e43b36' if q['net']=='VDD' else '#2976bd';mx,my,mxx,myy=q['m8']
  a.plot([x/D,x/D],[y/D,my/D],color=c,lw=.8);a.scatter([x/D],[my/D],s=6,color='k' if q['landing']=='M8_stripe' else '#7a3db8',zorder=5)
  if q['landing']=='M9_bridge':a.plot([mx/D,mxx/D],[my/D,myy/D],color='#7a3db8',lw=1.6)
  if tuple(q['rail']) in fk:r=q['rail'];a.add_patch(Rectangle((r[0]/D,r[1]/D-.05),(r[2]-r[0])/D,.1+(r[3]-r[1])/D,color='#1a9a50',zorder=6))
 a.set_xlim(x0/D,x1/D);a.set_ylim(y0/D,y1/D);a.set_aspect('equal');a.set_title(f'{bk} near ({cx/D:.1f}, {cy/D:.1f}) um\nblack dot = VIA78 on M8 stripe, purple = M8 bridge to M9, hatched = M8 clock leg',fontsize=9)
for a in aa.flat:a.set_xlabel('um');a.set_ylabel('um')
fig.savefig(out,dpi=150);print('wrote',out)
