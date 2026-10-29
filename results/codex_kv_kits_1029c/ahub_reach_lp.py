#!/usr/bin/env python3
"""Physical-only Manhattan reach estimate; fixed pins/macros and legal channel bounds."""
import json,sys,collections,copy
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as G
p=Path(sys.argv[1]);out=Path(sys.argv[2]);D=G.Design(p/'ahub.tsv')
face={r['id'] for r in json.load(open(p/'ahub_face_ff.json'))};seq={i for i,c in D.cells.items() if c[0]=='S'};comb={i for i,c in D.cells.items() if c[0] in 'BLK'}
ind=collections.Counter();succ=collections.defaultdict(list);st=collections.defaultdict(set);caps=collections.defaultdict(set)
for c in comb:
 for n in D.drives[c]:
  for s in D.nets[n][2]:
   if s[0]=='i' and not s[2] and s[1] in comb:succ[c].append(s[1]);ind[s[1]]+=1
for c in seq:
 for n in D.drives[c]:
  for s in D.nets[n][2]:
   if s[0]!='i' or s[2]:continue
   if s[1] in seq:caps[s[1]].add(c)
   elif s[1] in comb:st[s[1]].add(c)
q=collections.deque(c for c in comb if not ind[c])
while q:
 c=q.popleft()
 for n in D.drives[c]:
  for s in D.nets[n][2]:
   if s[0]!='i' or s[2]:continue
   if s[1] in seq:caps[s[1]].update(st[c])
   elif s[1] in comb:st[s[1]].update(st[c])
 for t in succ[c]:
  ind[t]-=1
  if ind[t]==0:q.append(t)
edges={(s,t) for t,ss in caps.items() for s in ss if s!=t};mov=sorted(seq-face);ix={c:4*i for i,c in enumerate(mov)};nv=4*len(mov)
rows=[];cols=[];vals=[];b=[]
def add(terms,rhs):
 r=len(b);b.append(rhs)
 for c,v in terms.items():
  if v:rows.append(r);cols.append(c);vals.append(v)
def reach(L):
 for s,t in edges:
  for sx,sy in [(1,1),(1,-1),(-1,1),(-1,-1)]:
   v={};rhs=L
   for c,z in [(s,1),(t,-1)]:
    if c in ix:
     for d,k in [(0,sx),(1,sy)]:v[ix[c]+d]=v.get(ix[c]+d,0)+z*k
    else:
     x,y=G.ctr(D.cells[c]);rhs-=z*(sx*x+sy*y)
   add(v,rhs)
reach(390)
for c in mov:
 i=ix[c];x,y=G.ctr(D.cells[c])
 for d,target in [(0,x),(1,y)]:add({i+d:1,i+d+2:-1},target);add({i+d:-1,i+d+2:-1},-target)
cost=np.zeros(nv)
for i in range(0,nv,4):cost[i+2]=1;cost[i+3]=1
bounds=[]
for c in mov:bounds.extend([(5,599),(5,435),(0,None),(0,None)])
A=coo_matrix((vals,(rows,cols)),shape=(len(b),nv)).tocsr()
r=linprog(cost,A_ub=A,b_ub=b,bounds=bounds,method='highs')
(out.parent/'ahub_seq_pairs.json').write_text(json.dumps(sorted(edges)))
report={'source_edges':len(edges),'fixed_face_flops':len(face),'movable_flops':len(mov),'relaxed_status':r.message}
if not r.success:out.write_text(json.dumps(report,indent=1));raise SystemExit(report)
# Decompose the real macro-free area into rectangles. Pick the nearest rectangle
# to the unconstrained optimum for each register, then solve all reach edges again.
mac=[c for c in D.cells.values() if c[0]=='M'];halo=2.16
xx=sorted({5.,599.}|{v for c in mac for v in (max(5,c[2]-halo),min(599,c[4]+halo))});yy=sorted({5.,435.}|{v for c in mac for v in (max(5,c[3]-halo),min(435,c[5]+halo))});rect=[]
for x0,x1 in zip(xx,xx[1:]):
 for y0,y1 in zip(yy,yy[1:]):
  if x1-x0<2 or y1-y0<1:continue
  x,y=(x0+x1)/2,(y0+y1)/2
  if any(c[2]-halo<x<c[4]+halo and c[3]-halo<y<c[5]+halo for c in mac):continue
  rect.append((x0+.6,y0+.2,x1-.6,y1-.2))
for c in mov:
 i=ix[c];x,y=r.x[i:i+2]
 def dist(a):return max(a[0]-x,0,x-a[2])+max(a[1]-y,0,y-a[3])
 a=min(rect,key=dist);bounds[i]=(a[0],a[2]);bounds[i+1]=(a[1],a[3])
r2=linprog(cost,A_ub=A,b_ub=b,bounds=bounds,method='highs');report['legal_channel_status']=r2.message
if r2.success:
 moves=[]
 for c in mov:
  i=ix[c];x,y=r2.x[i:i+2];cc=D.cells[c];w,h=cc[4]-cc[2],cc[5]-cc[3]
  if abs(x-G.ctr(cc)[0])+abs(y-G.ctr(cc)[1])>.1:moves.append({'id':c,'name':cc[6],'xy_center':[x,y],'old_center':G.ctr(cc),'bounds_xy':[bounds[i],bounds[i+1]]})
  D.cells[c]=cc[:2]+(x-w/2,y-h/2,x+w/2,y+h/2)+cc[6:]
 report['estimate']=G.r2r_metrics(D);report['moves']=moves;report['total_displacement_um']=r2.fun
out.write_text(json.dumps(report,indent=1)+'\n');print({k:v for k,v in report.items() if k!='moves'})
