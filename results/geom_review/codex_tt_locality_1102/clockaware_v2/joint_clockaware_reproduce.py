"""Finite joint same-edge homes repair; exact first-register neighbors, fixed clock inputs/macros/pins."""
from pathlib import Path
import json,re,collections,importlib.util
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import coo_matrix
P=Path(__file__).parent
spec=importlib.util.spec_from_file_location('g',P/'geom_rules.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
d=g.Design(P/'port_geom_repack3.tsv');orig=dict(d.cells);names={c[6]:i for i,c in d.cells.items()};baseline=json.loads((P/'homes_for_final_audit.json').read_text())
for h in baseline:
 i=names[h['name']];c=d.cells[i];x,y=h['xy'];w,hh=c[4]-c[2],c[5]-c[3];d.cells[i]=(c[0],c[1],x-w/2,y-hh/2,x+w/2,y+hh/2,c[6])
seq={i for i,c in d.cells.items() if c[0]=='S'};macros={i:c for i,c in d.cells.items() if c[0]=='M'};cache={}
def walk(i,fwd):
 if (i,fwd) in cache:return cache[i,fwd]
 todo=[i];seen=set();out=set()
 while todo:
  a=todo.pop()
  if a in seen:continue
  seen.add(a)
  ns=[z[1] for n in d.drives.get(a,[]) for z in d.nets[n][2] if z[0]=='i' and not z[2]] if fwd else [d.nets[n][1][1] for n,clk in d.cell_in.get(a,[]) if not clk and d.nets[n][1] and d.nets[n][1][0]=='i']
  for j in ns:
   if j in seq:out.add(j)
   elif d.kind(j) in 'BLK':todo.append(j)
 cache[i,fwd]=out;return out
report=json.loads((P/'final_composed_audit.json').read_text());seeds={names[z['name']] for z in report['body_fail']}
for z in report['reach_fail']:
 for key in ('launch','capture'):
  i=names[z[key]]
  if d.cells[i][0]=='S' and d.cells[i][1]!='REAL_MACRO_PORT':seeds.add(i)
  elif key=='capture' and d.cells[i][1]=='REAL_MACRO_PORT':
   # A macro address port has several possible register launchers. Include
   # every first-register source, not just the current worst-distance witness.
   seeds.update(j for j in walk(i,False) if d.cells[j][1]!='REAL_MACRO_PORT')
variables=set(seeds)
for i in list(seeds):
 variables.update(j for j in walk(i,False)|walk(i,True) if d.cells[j][6].startswith('u_bound.u_bout_tl/q'))
if any(d.cells[i][6].startswith('u_bound.u_cland_') for i in variables):raise RuntimeError('Regional origin consumer requires explicit source context; do not guess')
variables=sorted(variables);ix={i:k for k,i in enumerate(variables)};K=len(variables);N=4*K
pin_by_name={p['name']:p for p in d.pins};pin_targets={}
for i in variables:
 n=d.cells[i][6]
 if n.startswith('u_bound.u_bout_tl/'):
  m=re.search(r'/q\\\[([0-9]+)\\\]',n)
  if not m:raise RuntimeError('Missing exact output-pin association '+n)
  p=pin_by_name['tl['+m[1]+']'];pin_targets[i]=(p['x'],p['y'])
edges=set()
for i in variables:
 edges.update((j,i) for j in walk(i,False) if j!=i);edges.update((i,j) for j in walk(i,True) if j!=i)
print('CLOCKAWARE_JOINT_MODEL',len(seeds),'seeds',K,'variables',len(pin_targets),'actual TL pins<=30um',len(edges),'all first-register constraints',flush=True)
old={i:g.ctr(d.cells[i]) for i in variables};cuts=set();history=[]
for iteration in range(32):
 rows=[];bs=[]
 def add(r,b):rows.append(r);bs.append(b)
 for a,b in edges:
  for sx,sy in ((1,1),(1,-1),(-1,1),(-1,-1)):
   r={};limit=404.9999
   for n,sign in ((a,1),(b,-1)):
    if n in ix:
     k=ix[n];r[2*k]=sign*sx;r[2*k+1]=sign*sy
    else:
     x,y=g.ctr(d.cells[n]);limit-=sign*(sx*x+sy*y)
   add(r,limit)
 for i in variables:
  k=ix[i];x,y=old[i]
  for v,ref in ((0,x),(1,y)):
   add({2*k+v:1,2*K+2*k+v:-1},ref);add({2*k+v:-1,2*K+2*k+v:-1},-ref)
  if i in pin_targets:
   px,py=pin_targets[i]
   for sx,sy in ((1,1),(1,-1),(-1,1),(-1,-1)):add({2*k:sx,2*k+1:sy},30+sx*px+sy*py)
 expanded=N+4*len(cuts);MM=1600
 for ci,(i,mi) in enumerate(sorted(cuts)):
  k=ix[i];c=d.cells[i];m=macros[mi];hw=(c[4]-c[2])/2;hh=(c[5]-c[3])/2;bits=[N+4*ci+j for j in range(4)]
  for axis,sign,limit,bit in [(0,1,m[2]-hw-.0001,bits[0]),(0,-1,-m[4]-hw-.0001,bits[1]),(1,1,m[3]-hh-.0001,bits[2]),(1,-1,-m[5]-hh-.0001,bits[3])]:add({2*k+axis:sign,bit:MM},limit+MM)
  add({j:-1 for j in bits},-1)
 ri=[];cc=[];vv=[]
 for j,row in enumerate(rows):
  for col,v in row.items():ri.append(j);cc.append(col);vv.append(v)
 A=coo_matrix((vv,(ri,cc)),shape=(len(rows),expanded)).tocsr();low=np.r_[np.tile([4.9,4.5],K),np.zeros(2*K),np.zeros(expanded-N)];hi=np.r_[np.tile([772.7,513.9],K),np.full(2*K,np.inf),np.ones(expanded-N)]
 objective=np.r_[np.zeros(2*K),np.ones(2*K),np.zeros(expanded-N)]
 res=milp(objective,integrality=np.r_[np.zeros(N),np.ones(expanded-N)],bounds=Bounds(low,hi),constraints=LinearConstraint(A,np.full(len(bs),-np.inf),np.array(bs)))
 if res.x is None:
  print('CLOCKAWARE_JOINT_NO_SOLUTION',iteration,res.message,flush=True)
  (P/'joint_report.json').write_text(json.dumps(dict(status='NO_SOLUTION',message=res.message,history=history),indent=1));raise SystemExit(2)
 if np.max(A@res.x-np.array(bs))>1e-5:raise RuntimeError('Solver residual exceeded actual constraints')
 body=[]
 for i in variables:
  c=d.cells[i];k=ix[i];x,y=res.x[2*k:2*k+2];hw=(c[4]-c[2])/2;hh=(c[5]-c[3])/2;d.cells[i]=(c[0],c[1],x-hw,y-hh,x+hw,y+hh,c[6])
  for mi,m in macros.items():
   if min(x+hw,m[4])-max(x-hw,m[2])>1e-6 and min(y+hh,m[5])-max(y-hh,m[3])>1e-6:body.append((i,mi))
 history.append(dict(iteration=iteration,macro_cuts=len(cuts),body=len(body),movement=float(res.fun)))
 print('CLOCKAWARE_JOINT_ITER',history[-1],flush=True)
 if not body:break
 new=set(body)-cuts
 if not new:raise RuntimeError('Repeated body disjunction failed')
 cuts.update(new)
else:raise RuntimeError('Finite macro-cut exhaustion')
homes=[]
for i,c in d.cells.items():
 if c[0]!='S' or c[1]=='REAL_MACRO_PORT':continue
 pt=g.ctr(c);before=g.ctr(orig[i])
 if sum(abs(a-b) for a,b in zip(pt,before))>.01:homes.append(dict(id=i,name=c[6],old_xy=list(before),xy=list(pt)))
(P/'homes_for_final_audit.json').write_text(json.dumps(homes,separators=(',',':')))
points=[dict(name=d.cells[i][6],old_xy=old[i],xy=g.ctr(d.cells[i]),pin=pin_targets.get(i)) for i in variables]
(P/'joint_report.json').write_text(json.dumps(dict(status='PASS_LOCAL_CONSTRAINTS_ONLY',variables=K,all_first_register_edges=len(edges),TL_pin_budget=30,changes=points,history=history,cycles_added=0,ff_added=0,full45301_audit_required=True),indent=1))
print('CLOCKAWARE_JOINT_LOCAL_DONE',len(homes),'ordinaryFF guides; full45301 audit next',flush=True)
