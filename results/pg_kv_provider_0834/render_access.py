#!/usr/bin/env python3
"""Render actual cells, native supply rails and planned access in representative islands."""
import argparse,json,collections
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

def render(src,plan,out):
 g=json.load(open(Path(src)/'geometry.json'));p=json.load(open(Path(plan)/'access_plan.json'));D=g['dbu']
 cells=g['cells'];bins=collections.Counter((int(q['bbox_dbu'][0]/D/100),int(q['bbox_dbu'][1]/D/100)) for q in cells)
 centers=[((i+.5)*100,(j+.5)*100) for (i,j),_ in bins.most_common(3)]
 fig,aa=plt.subplots(2,2,figsize=(15,11),constrained_layout=True);ax=aa.flat[0]
 ax.scatter([(q['bbox_dbu'][0]+q['bbox_dbu'][2])/2/D for q in cells],[(q['bbox_dbu'][1]+q['bbox_dbu'][3])/2/D for q in cells],s=.3,color='black',rasterized=True)
 ax.set_title(f"KV actual infrastructure: {len(cells):,} cells / {len(p['paths']):,} PG groups")
 ax.set_xlim(0,g['die_dbu'][2]/D);ax.set_ylim(0,g['die_dbu'][3]/D);ax.set_aspect('equal')
 for a,(cx,cy) in zip(list(aa.flat)[1:],centers):
  w=50;x0,y0,x1,y1=cx-w,cy-w,cx+w,cy+w
  for q in cells:
   x,y,xx,yy=[v/D for v in q['bbox_dbu']]
   if x>x1 or xx<x0 or y>y1 or yy<y0:continue
   a.add_patch(Rectangle((x,y),xx-x,yy-y,facecolor='#b8bbc2',edgecolor='gray',linewidth=.2))
  for q in p['paths']:
   x,y=q['stack'];x/=D;y/=D
   if not x0<=x<=x1 or not y0<=y<=y1:continue
   mx,my,mxx,myy=[v/D for v in q['m8']];a.plot([mx,mxx],[my,myy],color='#e43b36' if q['net']=='VDD' else '#2976bd',lw=.5)
   a.plot([x,x],[y,my],color='#e43b36' if q['net']=='VDD' else '#2976bd',lw=.5)
   a.scatter([x],[y],s=3,color='#e43b36' if q['net']=='VDD' else '#2976bd')
  a.set_xlim(x0,x1);a.set_ylim(y0,y1);a.set_aspect('equal');a.set_title(f'Actual dense island near ({cx:.0f}, {cy:.0f}) um')
 for a in aa.flat:a.set_xlabel('um');a.set_ylabel('um')
 fig.savefig(out,dpi=170)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--source',required=True);a.add_argument('--plan',required=True);a.add_argument('--out',required=True);q=a.parse_args();render(q.source,q.plan,q.out)
