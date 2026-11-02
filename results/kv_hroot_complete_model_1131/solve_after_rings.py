from pathlib import Path
import json,sys,numpy as np
from scipy.optimize import linprog
from scipy.sparse import lil_matrix
import geom_rules as G
R=Path('/home/ubuntu/coord/tmp/codex-kv-hroot/actual_fix')
D=G.Design(str(R/'model_ring.tsv'))
bad=[];G.r2r_metrics(D,capture_pairs=bad)
names={p[k] for p in bad for k in ('launch','capture')}
# Move existing native endpoint flops only; landing rings and declared reset relays stay fixed.
sel=[i for i,c in D.cells.items() if c[0]=='S' and any(s in c[6] for s in ('u_bin_','u_bout_','u_ist_','u_u_efault.','u_u_fch.'))]
idx={i:k for k,i in enumerate(sel)};edges=set();pins=set()
for target in sel:
 for rev in (True,False):
  seen=set();stack=[target]
  while stack:
   cur=stack.pop();refs=[]
   if rev:
    for n,ck in D.cell_in.get(cur,[]):
     if not ck and D.nets[n][1]:refs.append(D.nets[n][1])
   else:
    for n in D.drives.get(cur,[]):refs.extend(s for s in D.nets[n][2] if not s[2])
   for ref in refs:
    kind,j,ck=ref
    if ck:continue
    if kind=='p':pins.add((target,j));continue
    if D.kind(j)=='S':edges.add((j,target) if rev else (target,j))
    elif D.kind(j) in 'BLK' and j not in seen:seen.add(j);stack.append(j)
rows=[];bs=[];labels=[];n=len(sel)
from collections import defaultdict
fixed=defaultdict(set)
for a,b in edges:
 if a in idx and b not in idx:fixed[a].add(b)
 if b in idx and a not in idx:fixed[b].add(a)
viol=[]
for i,ns in fixed.items():
 for axis in (0,1):
  vals=[(G.ctr(D.cells[j])[0]+(1 if axis==0 else -1)*G.ctr(D.cells[j])[1],j) for j in ns]
  lo=min(vals);hi=max(vals)
  if hi[0]-lo[0]>780:viol.append(dict(movable=D.cells[i][6],span=hi[0]-lo[0],fixed=[D.cells[lo[1]][6],D.cells[hi[1]][6]]))
print('fixed infeasible',json.dumps(viol[:15]),flush=True)
(R/'infeasible_fixed.json').write_text(json.dumps(viol,indent=2))
def limit(a,b,dist):
 for sx,sy in ((1,1),(1,-1),(-1,1),(-1,-1)):
  row={};const=0
  for i,sgn in ((a,1),(b,-1)):
   if isinstance(i,int) and i in idx:
    k=idx[i];row[2*k]=row.get(2*k,0)+sgn*sx;row[2*k+1]=row.get(2*k+1,0)+sgn*sy
   else:
    x,y=G.ctr(D.cells[i]) if isinstance(i,int) else i;const+=sgn*(sx*x+sy*y)
  
  if a==b:assert not any(row.values()) and abs(const)<1e-8
  rows.append(row);bs.append(dist-const);labels.append((D.cells[a][6] if isinstance(a,int) else a,D.cells[b][6] if isinstance(b,int) else b,dist))
for a,b in edges:
 if '--reset-repoint' in sys.argv and 'u_rrl_' in D.cells[a][6] and b in idx:continue
 limit(a,b,394)
for i,p in ([] if '--no-pins' in sys.argv else pins):
 pin=D.pin_by_k[p];limit(i,(pin['x'],pin['y']),25)
nreach=len(rows)
for i,k in idx.items():
 for ax,val in enumerate(G.ctr(D.cells[i])):
  for sg in (-1,1):rows.append({2*k+ax:sg,2*n+2*k+ax:-1});bs.append(sg*val)
A=lil_matrix((len(rows),4*n+1))
for r,row in enumerate(rows):
 for c,v in row.items():A[r,c]=v
A[:nreach,4*n]=-1
res=linprog(np.r_[np.zeros(2*n),np.ones(2*n),100000],A_ub=A.tocsr(),b_ub=bs,bounds=[(6,1894),(6,832)]*n+[(0,None)]*(2*n)+[(0,None)],method='highs')
if res.success:
 print('required extra reach',res.x[-1],flush=True)
 print('critical_constraints',[(labels[i],round(float(v),2)) for i,v in enumerate(res.ineqlin.marginals[:nreach]) if abs(v)>100],flush=True)
print(n,len(edges),len(pins),res.message,flush=True)
payload={'status':res.message,'selected':n,'edges':len(edges),'pins':len(pins),'moves':[]}
if res.success:
 for i,k in idx.items():
  xy=res.x[2*k:2*k+2];old=G.ctr(D.cells[i]);delta=sum(abs(x-y) for x,y in zip(xy,old))
  if delta>.05:
   payload['moves'].append(dict(name=D.cells[i][6],old=old,new=list(xy),move_um=round(delta,3)))
   c=list(D.cells[i]);dx,dy=xy[0]-old[0],xy[1]-old[1];c[2]+=dx;c[4]+=dx;c[3]+=dy;c[5]+=dy;D.cells[i]=tuple(c)
 b2=[];payload['full_r2r']=G.r2r_metrics(D,capture_pairs=b2);payload['residual_bad']=b2;print(payload['full_r2r'],flush=True);print(json.dumps(sorted(b2,key=lambda x:-x['distance_um'])[:8]),flush=True)
(R/'proposal_after_rings.json').write_text(json.dumps(payload,indent=2))
