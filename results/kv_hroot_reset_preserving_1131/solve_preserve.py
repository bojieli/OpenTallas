"""Source-preserving geometry feasibility; never rewrites any net/cell source."""
from pathlib import Path
import json,numpy as np,re
from scipy.optimize import linprog
from scipy.sparse import lil_matrix
import geom_rules as G
R=Path(__file__).resolve().parent; D=G.Design(R/'complete_model.tsv')
graph=json.loads((R/'native_reset_source_graph.json').read_text()); rnames={'u_bound.'+s['instance']+'/q$_DFF_P_' for v in graph.values() for s in v['path']};assert len(rnames)==180
sel=[i for i,c in D.cells.items() if c[0]=='S' and (c[-1] in rnames or any(t in c[-1] for t in ('u_bin_','u_bout_','u_ist_','u_u_efault.','u_u_fch.')))]
assert rnames<={D.cells[i][-1] for i in sel}
idx={i:k for k,i in enumerate(sel)};edges=set();pins=set()
for target in sel:
 for rev in (True,False):
  seen=set();stack=[target]
  while stack:
   cur=stack.pop();refs=[]
   if rev:
    refs=[D.nets[n][1] for n,ck in D.cell_in.get(cur,[]) if not ck and D.nets[n][1]]
   else:
    for n in D.drives.get(cur,[]):refs.extend(s for s in D.nets[n][2] if not s[2])
   for kind,j,ck in refs:
    if ck:continue
    if kind=='p':pins.add((target,j))
    elif D.kind(j)=='S':edges.add((j,target) if rev else (target,j))
    elif D.kind(j) in 'BLK' and j not in seen:seen.add(j);stack.append(j)
n=len(sel)
def solve(reach,pinmax,relax=False):
 rows=[];rhs=[];labels=[]
 def lim(a,b,dist,kind):
  for sx,sy in ((1,1),(1,-1),(-1,1),(-1,-1)):
   row={};const=0
   for node,sgn in ((a,1),(b,-1)):
    if isinstance(node,int) and node in idx:
     k=idx[node]
     row[2*k]=row.get(2*k,0)+sgn*sx;row[2*k+1]=row.get(2*k+1,0)+sgn*sy
    else:
     x,y=G.ctr(D.cells[node]) if isinstance(node,int) else node
     const+=sgn*(sx*x+sy*y)
   if a==b:assert not any(row.values()) and abs(const)<1e-7
   rows.append(row);rhs.append(dist-const)
   labels.append(dict(kind=kind,a=D.cells[a][-1] if isinstance(a,int) else a,b=D.cells[b][-1] if isinstance(b,int) else b,limit_um=dist,sign=[sx,sy]))
 for a,b in sorted(edges):lim(a,b,reach,'existing_native_sequential_edge')
 for i,p in sorted(pins):
  v=D.pin_by_k[p];lim(i,(v['x'],v['y']),pinmax,'actual_typed_pin:'+v['name'])
 nr=len(rows)
 for i,k in idx.items():
  for ax,value in enumerate(G.ctr(D.cells[i])):
   for sign in (-1,1):rows.append({2*k+ax:sign,2*n+2*k+ax:-1});rhs.append(sign*value)
 cols=4*n+int(relax);A=lil_matrix((len(rows),cols))
 for r,row in enumerate(rows):
  for c,v in row.items():A[r,c]=v
 if relax:A[:nr,4*n]=-1
 c=np.r_[np.zeros(2*n),np.ones(2*n),[1000000] if relax else []]
 result=linprog(c,A_ub=A.tocsr(),b_ub=rhs,bounds=[(6,1894),(6,832)]*n+[(0,None)]*(2*n)+([(0,None)] if relax else []),method='highs')
 out=dict(reach_um=reach,pin_um=pinmax,relaxed_diagnostic_only=relax,status=result.message,success=result.success)
 if result.success:
  out['required_extra_um']=float(result.x[-1]) if relax else 0
  out['dual_cut']=[dict(labels[k],dual=float(v)) for k,v in enumerate(result.ineqlin.marginals[:nr]) if abs(v)>1e-6]
  out['moves']=[dict(name=D.cells[i][-1],reset_relay=D.cells[i][-1] in rnames,old=list(G.ctr(D.cells[i])),new=list(result.x[2*k:2*k+2]),distance_um=float(sum(abs(a-b) for a,b in zip(G.ctr(D.cells[i]),result.x[2*k:2*k+2])))) for i,k in idx.items() if sum(abs(a-b) for a,b in zip(G.ctr(D.cells[i]),result.x[2*k:2*k+2]))>.001]
 return out
out=dict(scope='PREP source-preserving geometry feasibility only. All original nets/reset180FF/7depth/root/input positions retained. No repoint/new FF/cycle/source/ODB change. Clock/footprint qualification follows only if point model feasible.',selected=n,existing_reset_relays=180,all_edges=len(edges),all_actual_pin_obligations=len(pins),fixed_root_input_names=[c[-1] for i,c in D.cells.items() if 'u_rst_in/' in c[-1]],variants=[])
for reach,pin in [(394,30),(405,150)]:
 v=solve(reach,pin);out['variants'].append(v);print(reach,pin,v['status'],flush=True)
 if not v['success']:
  z=solve(reach,pin,True);out['variants'].append(z);print('diagnostic extra',z.get('required_extra_um'),flush=True)
(R/'source_preserving_feasibility.json').write_text(json.dumps(out,indent=2))
