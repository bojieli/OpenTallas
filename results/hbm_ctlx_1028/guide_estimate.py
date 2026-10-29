#!/usr/bin/env python3
import json,sys,collections,pickle
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'/'autopilot'))
import geom_rules as G
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import lil_matrix
P=Path(__file__).parent
D=G.Design(sys.argv[1]);bad=json.load(open(sys.argv[2]))['bad_pairs'];nameid={c[6]:i for i,c in D.cells.items()};names={i:c[6] for i,c in D.cells.items()}
# Move internal source of each bad leg; a face input cannot move, so move its internal consumer.
move=set(nameid[b['dst'] if b['src'].startswith('u_bin_') else b['src']] for b in bad)
seq=[i for i,c in D.cells.items() if c[0]=='S'];bit={i:1<<n for n,i in enumerate(seq)};comb={i for i,c in D.cells.items() if c[0] in 'BLK'}
ind=collections.Counter();succ=collections.defaultdict(list);bs={};caps=collections.defaultdict(int)
for i in comb:
 for ni in D.drives.get(i,[]):
  for s in D.nets[ni][2]:
   if s[0]=='i' and not s[2] and s[1] in comb:succ[i].append(s[1]);ind[s[1]]+=1
for i in seq:
 for ni in D.drives.get(i,[]):
  for s in D.nets[ni][2]:
   if s[0]!='i' or s[2]:continue
   if s[1] in bit:caps[s[1]]|=bit[i]
   elif s[1] in comb:bs[s[1]]=bs.get(s[1],0)|bit[i]
q=collections.deque(i for i in comb if ind[i]==0)
while q:
 i=q.popleft();b=bs.get(i,0)
 for ni in D.drives.get(i,[]):
  for s in D.nets[ni][2]:
   if s[0]!='i' or s[2]:continue
   if s[1] in bit:caps[s[1]]|=b
   elif s[1] in comb:bs[s[1]]=bs.get(s[1],0)|b
 for j in succ[i]:
  ind[j]-=1
  if ind[j]==0:q.append(j)
# Worst-per-capture receipt hides alternate launchers. Include every actual bad pair before choosing movable cells.
xy={i:G.ctr(c) for i,c in D.cells.items()}
for j,b in caps.items():
 while b:
  lo=b&-b;i=seq[lo.bit_length()-1];b-=lo
  if abs(xy[i][0]-xy[j][0])+abs(xy[i][1]-xy[j][1])>385:
   move.add(j if names[i].startswith("u_bin_") else i)
# Keep every physical sequential pair that touches a moved register. Other unchanged pairs are checked by canonical census.
mb=0
for i in move:mb|=bit[i]
pairs=[]
for j,b in caps.items():
 b=b if j in move else b&mb
 while b:
  lo=b&-b;n=lo.bit_length()-1;i=seq[n];b-=lo;pairs.append((i,j))
print('movable',len(move),'incidentpairs',len(pairs),'caps',len(caps),flush=True)
move=sorted(move);mi={i:k for k,i in enumerate(move)};N=len(move);rows=[];rhs=[]
xy={i:G.ctr(c) for i,c in D.cells.items()};target=385.0
# L1 balls = four halfplanes. Minimize displacement from original positions, keeping all incident edges within target.
for i,j in pairs:
 if i==j:continue
 for sx,sy in [(1,1),(1,-1),(-1,1),(-1,-1)]:
  r={};b=target
  for c,sgn in [(i,1),(j,-1)]:
   if c in mi:
    r[2*mi[c]]=r.get(2*mi[c],0)+sgn*sx;r[2*mi[c]+1]=r.get(2*mi[c]+1,0)+sgn*sy
   else:b-=sgn*(sx*xy[c][0]+sy*xy[c][1])
  rows.append(r);rhs.append(b)
for i,k in mi.items():
 for d in range(2):
  for sign in [1,-1]:rows.append({2*k+d:sign,2*N+2*k+d:-1});rhs.append(sign*xy[i][d])
A=lil_matrix((len(rows),4*N))
for n,r in enumerate(rows):
 for k,v in r.items():A[n,k]=v
bounds=[(12,379),(12,404)]*N+[(0,None)]*(2*N)
res=linprog([0]*(2*N)+[1]*(2*N),A_ub=A.tocsr(),b_ub=rhs,bounds=bounds,method='highs')
if not res.success:print(res.message);sys.exit(2)
# Keep guide boxes outside the SRAM+halo and island footprints. Pick the nearest legal half-plane, then resolve.
obstacles=[(139.806,194.46,251.886,252.84)]
infra=json.load(open(sys.argv[3]))
obstacles+=list({tuple([round(v-4.32,6) for v in c['rect_um'][:2]]+[round(v+4.32,6) for v in c['rect_um'][2:]]) for c in infra['cells']})
from scipy.sparse import vstack, csr_matrix
fixed_sides=set()
for it in range(12):
 extra=[];extra_rhs=[]
 for i,k in mi.items():
  x,y=res.x[2*k:2*k+2]
  for ob,(x0,y0,x1,y1) in enumerate(obstacles):
   if x0<x<x1 and y0<y<y1:
    opts=[(x-x0,0,1,x0),(x1-x,0,-1,-x1),(y-y0,1,1,y0),(y1-y,1,-1,-y1)]
    _,dim,sgn,b=min(opts)
    key=(i,ob,dim,sgn)
    if key in fixed_sides:raise RuntimeError('unresolved obstacle')
    fixed_sides.add(key);r=lil_matrix((1,4*N));r[0,2*k+dim]=sgn;extra.append(r.tocsr());extra_rhs.append(b)
 if not extra:break
 A=vstack([A]+extra);rhs=list(rhs)+extra_rhs
 res=linprog([0]*(2*N)+[1]*(2*N),A_ub=A.tocsr(),b_ub=rhs,bounds=bounds,method='highs')
 if not res.success:print('obstacle infeasible',res.message);sys.exit(3)
centers={i:(float(res.x[2*k]),float(res.x[2*k+1])) for i,k in mi.items()};out=[]
for i in move:
 x,y=centers[i];out.append(dict(name=names[i],old_xy_um=xy[i],new_xy_um=[round(x,3),round(y,3)]))
# Apply centres in memory and re-run canonical full-graph extrema census.
for i,(x,y) in centers.items():
 c=D.cells[i];hw=(c[4]-c[2])/2;hh=(c[5]-c[3])/2;D.cells[i]=(c[0],c[1],x-hw,y-hh,x+hw,y+hh,c[6])
after=G.r2r_metrics(D);print(after,flush=True)
report=dict(movable=len(move),incident_pairs=len(pairs),target_um=target,canonical_after=after,moves=out)
(P/'guide_estimate.json').write_text(json.dumps(report,indent=2)+'\n')
