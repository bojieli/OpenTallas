#!/usr/bin/env python3
"""Dump partition outlines, master M1 OBS (die coords), std cells and hard rects inside a window (um) for rendering.
openroad -python -no_init -exit dump_render.py --odb X --hard constraints.json --win x0 y0 x1 y1 --out dump.json"""
import argparse,json
import odb
p=argparse.ArgumentParser();p.add_argument('--odb',required=True);p.add_argument('--hard');p.add_argument('--win',nargs=4,type=float,required=True);p.add_argument('--out',required=True);a=p.parse_args()
d=odb.dbDatabase.create();odb.read_db(d,a.odb);b=d.getChip().getBlock();U=b.getDbUnitsPerMicron();W=[round(v*U) for v in a.win]
def RB(x):return (x.xMin(),x.yMin(),x.xMax(),x.yMax())
def hit(r,q):return r[0]<q[2] and q[0]<r[2] and r[1]<q[3] and q[1]<r[3]
OR={'R0':lambda x,y:(x,y),'R90':lambda x,y:(-y,x),'R180':lambda x,y:(-x,-y),'R270':lambda x,y:(y,-x),'MY':lambda x,y:(-x,y),'MX':lambda x,y:(x,-y),'MXR90':lambda x,y:(y,x),'MYR90':lambda x,y:(-y,-x)}
def mk(i):
 f=OR[str(i.getOrient())];m=i.getMaster();bb=RB(i.getBBox());c=[f(x,y) for x,y in((0,0),(m.getWidth(),m.getHeight()))];dx=bb[0]-min(q[0] for q in c);dy=bb[1]-min(q[1] for q in c)
 def T(box):
  c=[f(x,y) for x,y in((box[0],box[1]),(box[2],box[3]))];return (min(q[0] for q in c)+dx,min(q[1] for q in c)+dy,max(q[0] for q in c)+dx,max(q[1] for q in c)+dy)
 return T
out=dict(win=a.win,parts=[],obs=[],clock=[],provider=[],hard=[],die=RB(b.getDieArea()),allclock=[])
for i in b.getInsts():
 r=RB(i.getBBox())
 if i.getMaster().isBlock():
  out['parts'].append((i.getName(),*r))
  if hit(r,W):
   T=mk(i)
   for o in i.getMaster().getObstructions():
    if o.getTechLayer() and o.getTechLayer().getName()=='M1':
     q=T(RB(o))
     if hit(q,W):out['obs'].append(q)
 else:
  k='clock' if i.getName().startswith('ck_') else 'provider'
  if k=='clock':out['allclock'].append(((r[0]+r[2])//2,(r[1]+r[3])//2))
  if hit(r,W):out[k].append(r)
if a.hard:
 out['hard']=[r[1:] for r in json.load(open(a.hard))['hard_forbidden']]
json.dump(out,open(a.out,'w'));print({k:len(v) for k,v in out.items() if isinstance(v,list)})
