#!/usr/bin/env python3
"""Actual placed-graph structural candidate; no netlist/latency changes."""
import sys,json,inspect,collections
from pathlib import Path
import numpy as np
from scipy.optimize import linprog, milp, Bounds, LinearConstraint
from scipy.sparse import lil_matrix
sys.path.insert(0,str(Path(sys.argv[1])/'tools/autopilot'))
import geom_rules as G
D=G.Design(sys.argv[2]); arcs=[]
s=inspect.getsource(G.r2r_metrics).replace('u0,u1,v0,v1=bounds(cap)','u0,u1,v0,v1=bounds(cap)\n        for e in lst:\n            arcs.extend((a,cap) for a in e[4:])')
ns=dict(G.__dict__,arcs=arcs);exec(s,ns);before=ns['r2r_metrics'](D)
arcs=set(arcs)
baseD=G.Design(sys.argv[2])
basepos={i:G.ctr(c) for i,c in baseD.cells.items()}
macro_cuts=set()
for iteration in range(40):
 pos=basepos
 D=G.Design(sys.argv[2])
 long=[(a,b) for a,b in arcs if sum(abs(pos[a][j]-pos[b][j]) for j in (0,1))>405]
 fixed=lambda i:pos[i][0]<12 or pos[i][1]<12
 moving=sorted({i for a,b in long for i in (a,b) if not fixed(i)})
 idx={i:j for j,i in enumerate(moving)};n=len(moving)
 # u=x+y, v=x-y permit exact Manhattan inequalities; L1 movement auxiliaries.
 rows=[];rhs=[]
 for a,b in arcs:
  if a not in idx and b not in idx:continue
  for coord in (0,1):
   for sign in (-1,1):
    row={};z=0
    for i,k in ((a,sign),(b,-sign)):
     if i in idx:row[2*idx[i]+coord]=k
     else:z+=k*(sum(pos[i]) if coord==0 else pos[i][0]-pos[i][1])
    rows.append(row);rhs.append(390-z)
 for i,j in idx.items():
  for c,target in enumerate((sum(pos[i]),pos[i][0]-pos[i][1])):
   for sign in (-1,1):rows.append({2*j+c:sign,2*n+2*j+c:-1});rhs.append(sign*target)
 kbin=4*n
 for i,mid in sorted(macro_cuts):
  if i not in idx:continue
  j=idx[i];c=baseD.cells[i];m=baseD.cells[mid];w,h=c[4]-c[2],c[5]-c[3]
  sides=[(0,1,m[2]-1-w/2),(0,-1,m[4]+1+w/2),(1,1,m[3]-1-h/2),(1,-1,m[5]+1+h/2)]
  for ax,sign,limit in sides:
   rows.append({2*j:sign*.5,2*j+1:sign*(.5 if ax==0 else -.5),kbin:2000});rhs.append(sign*limit+2000);kbin+=1
  rows.append({z:-1 for z in range(kbin-4,kbin)});rhs.append(-1)
 A=lil_matrix((len(rows),kbin))
 for r,row in enumerate(rows):
  for k,v in row.items():A[r,k]=v
 cost=np.r_[np.zeros(2*n),np.ones(2*n),np.zeros(kbin-4*n)]
 low=np.r_[np.full(2*n,-np.inf),np.zeros(kbin-2*n)]
 high=np.r_[np.full(4*n,np.inf),np.ones(kbin-4*n)]
 integer=np.r_[np.zeros(4*n),np.ones(kbin-4*n)]
 res=milp(cost,integrality=integer,bounds=Bounds(low,high),constraints=LinearConstraint(A.tocsc(),np.full(len(rows),-np.inf),rhs))
 out={'before':before,'long_arcs':len(long),'moving_candidates':n,'constraints':len(rows),'success':res.success,'message':res.message}
 if res.success:
  targets=[]
  for i,j in idx.items():
   u,v=res.x[2*j:2*j+2];x,y=(u+v)/2,(u-v)/2;c=D.cells[i];old=pos[i]
   if abs(x-old[0])+abs(y-old[1])<.001:continue
   targets.append({'name':c[6],'master':c[1],'old_centre':old,'target_centre':[round(x,4),round(y,4)],'old_bbox':list(c[2:6])})
   dx,dy=x-old[0],y-old[1];D.cells[i]=c[:2]+(c[2]+dx,c[3]+dy,c[4]+dx,c[5]+dy)+c[6:]
  out['targets']=targets;out['after_unlegalized']=G.r2r_metrics(D);out['iteration']=iteration
  out['max_displacement_um']=max((sum(abs(t['target_centre'][j]-t['old_centre'][j]) for j in (0,1)) for t in targets),default=0)
 if not res.success:break
 macro_hits=[]
 for i,j in idx.items():
  c=D.cells[i];x,y=G.ctr(c);old=pos[i];w,h=c[4]-c[2],c[5]-c[3]
  for mid,m in D.cells.items():
   if m[0]!='M':continue
   if c[4]<=m[2]-1+1e-6 or c[2]>=m[4]+1-1e-6 or c[5]<=m[3]-1+1e-6 or c[3]>=m[5]+1-1e-6:continue
   macro_hits.append(i);macro_cuts.add((i,mid))
 out['macro_hits_unlegalized']=len(set(macro_hits));out['macro_avoidance_cuts']=len(macro_cuts)
 if out['after_unlegalized']['r2r_captures_gt405']==0 and not macro_hits:break
 print('ITER',iteration,out['after_unlegalized']['r2r_captures_gt405'],len(macro_hits),file=sys.stderr,flush=True)
 ns['r2r_metrics'](D)
 arcs.update(ns['arcs'])
print(json.dumps(out,indent=1))
