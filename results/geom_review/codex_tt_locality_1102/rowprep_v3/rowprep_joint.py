"""Joint exact native-site completion of the finite cells that a single-cell move could not place."""
from pathlib import Path
script=Path(__file__).with_name('rowprep_greedy.py').read_text().split('# Place the most constrained')[0]
script=script.replace("P/'final_composed_homes_DISABLED.json'","P/'rowprep_homes.json'")
exec(compile(script,'rowprep_common','exec'))
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import coo_matrix
report=json.loads((P/'rowprep_report.json').read_text());seed={names[n] for n in report['failed']};joint=set(seed)
for i in seed:joint.update(j for j in adj[i] if isinstance(j,int) and j in variables)
joint=sorted(joint);jset=set(joint);ix={i:k for k,i in enumerate(joint)};K=len(joint);N=4*K
edge_subset={(a,b) for a,b in edges if a in jset or b in jset};goal={i:g.ctr(d.cells[i]) for i in joint};cuts=set();history=[]
# Existing unmoved/greedily placed FFs and all16 explicitly retained source slots
# are physical obstacles. Combinational cells are left to normal future placement.
fixed_boxes={i:list(c[2:6]) for i,c in d.cells.items() if c[0]=='S' and c[1]!='REAL_MACRO_PORT' and i not in jset and i not in oinv}
for k,h in enumerate(source):fixed_boxes[-k-1]=h['box']
macro_boxes={i:list(c[2:6]) for i,c in d.cells.items() if c[0]=='M'}
bins=collections.defaultdict(set)
for i,b in fixed_boxes.items():
 for x in range(int(b[0]//8.64),int(b[2]//8.64)+1):
  for y in range(int(b[1]//8.64),int(b[3]//8.64)+1):bins[x,y].add(i)
print('ROW_JOINT_MODEL',len(seed),'seeds',K,'coupled variables',len(edge_subset),'typed edges',len(fixed_boxes),'fixed FF/source obstacles',flush=True)
for iteration in range(64):
 rows=[];bs=[]
 def add(row,b):rows.append(row);bs.append(b)
 def expression(node,sx,sy,sign,row):
  if node in ix:
   c=d.cells[node];k=ix[node];row[2*k]=row.get(2*k,0)+sign*sx*.054;row[2*k+1]=row.get(2*k+1,0)+sign*sy*.27
   return sign*(sx*(c[4]-c[2])/2+sy*(c[5]-c[3])/2)
  x,y=point(node);return sign*(sx*x+sy*y)
 for a,b in edge_subset:
  for sx,sy in ((1,1),(1,-1),(-1,1),(-1,-1)):
   row={};constant=expression(a,sx,sy,1,row)+expression(b,sx,sy,-1,row);add(row,405.0-constant)
 for i in joint:
  k=ix[i];c=d.cells[i];hw,hh=(c[4]-c[2])/2,(c[5]-c[3])/2;x,y=goal[i]
  for axis,step,half,target in [(0,.054,hw,x),(1,.27,hh,y)]:
   add({2*k+axis:step,2*K+2*k+axis:-1},target-half);add({2*k+axis:-step,2*K+2*k+axis:-1},half-target)
  tap=pins[assign[c[6]]];other=[(tap['x'],tap['y'],200.0)]
  if i in pin_targets:other.append((*pin_targets[i],30.0))
  for x0,y0,r in other:
   for sx,sy in ((1,1),(1,-1),(-1,1),(-1,-1)):add({2*k:sx*.054,2*k+1:sy*.27},r+sx*(x0-hw)+sy*(y0-hh))
 expanded=N+4*len(cuts);MM=1600.0
 for oi,(i,kind,j) in enumerate(sorted(cuts)):
  k=ix[i];c=d.cells[i];w,hh=c[4]-c[2],c[5]-c[3];bits=[N+4*oi+t for t in range(4)]
  if kind=='J':
   kk=ix[j];cc=d.cells[j];ww,hj=cc[4]-cc[2],cc[5]-cc[3]
   choices=[({2*k:.054,2*kk:-.054},-w),({2*kk:.054,2*k:-.054},-ww),({2*k+1:.27,2*kk+1:-.27},-hh),({2*kk+1:.27,2*k+1:-.27},-hj)]
  else:
   x0,y0,x1,y1=(macro_boxes if kind=='M' else fixed_boxes)[j]
   choices=[({2*k:.054},x0-w),({2*k:-.054},-x1),({2*k+1:.27},y0-hh),({2*k+1:-.27},-y1)]
  for (row,b),bit in zip(choices,bits):row[bit]=MM;add(row,b+MM)
  add({bit:-1 for bit in bits},-1)
 ri=[];ci=[];vv=[]
 for n,row in enumerate(rows):
  for j,v in row.items():ri.append(n);ci.append(j);vv.append(v)
 A=coo_matrix((vv,(ri,ci)),shape=(len(rows),expanded)).tocsr();lo=[];hi=[]
 for i in joint:
  c=d.cells[i];w,hh=c[4]-c[2],c[5]-c[3];lo.extend([math.ceil(4.32/.054-1e-7),math.ceil(4.32/.27-1e-7)]);hi.extend([math.floor((773.28-w)/.054+1e-7),math.floor((514.08-hh)/.27+1e-7)])
 lo=np.r_[lo,np.zeros(2*K),np.zeros(expanded-N)];hi=np.r_[hi,np.full(2*K,np.inf),np.ones(expanded-N)]
 objective=np.r_[np.zeros(2*K),np.ones(2*K),np.zeros(expanded-N)];integ=np.r_[np.ones(2*K),np.zeros(2*K),np.ones(expanded-N)]
 result=milp(objective,integrality=integ,bounds=Bounds(lo,hi),constraints=LinearConstraint(A,np.full(len(bs),-np.inf),np.array(bs)))
 if result.x is None:
  (P/'rowjoint_report.json').write_text(json.dumps(dict(status='FINITE_COMPONENT_NO_SOLUTION',message=result.message,variables=K,history=history),indent=1));print('ROW_JOINT_NO_SOLUTION',result.message,flush=True);raise SystemExit(2)
 if np.max(A@result.x-np.array(bs))>1e-5:raise RuntimeError('Invalid joint row solver residual')
 collisions=set()
 for i in joint:
  k=ix[i];c=d.cells[i];w,hh=c[4]-c[2],c[5]-c[3];x=round(result.x[2*k])*.054;y=round(result.x[2*k+1])*.27;d.cells[i]=(c[0],c[1],x,y,x+w,y+hh,c[6])
 def overlap(a,b):return min(a[2],b[2])-max(a[0],b[0])>1e-6 and min(a[3],b[3])-max(a[1],b[1])>1e-6
 for i in joint:
  box=d.cells[i][2:6]
  for j,b in macro_boxes.items():
   if overlap(box,b):collisions.add((i,'M',j))
  nearby=set()
  for x in range(int(box[0]//8.64),int(box[2]//8.64)+1):
   for y in range(int(box[1]//8.64),int(box[3]//8.64)+1):nearby.update(bins[x,y])
  for j in nearby:
   if overlap(box,fixed_boxes[j]):collisions.add((i,'F',j))
  for j in joint:
   if j>i and overlap(box,d.cells[j][2:6]):collisions.add((i,'J',j))
 summary=dict(iteration=iteration,cuts=len(cuts),collisions=len(collisions),movement=float(result.fun));history.append(summary);print('ROW_JOINT_ITER',summary,flush=True)
 if not collisions:break
 new=collisions-cuts
 if not new:raise RuntimeError('Repeated collision despite an installed disjunction')
 cuts.update(new)
else:raise RuntimeError('Finite joint cut exhaustion; no global infeasibility conclusion')
rows=[dict(id=i,name=d.cells[i][6],old_xy=list(g.ctr(orig[i])),xy=list(g.ctr(d.cells[i]))) for i in sorted(variables)]
(P/'rowprep_complete_homes.json').write_text(json.dumps(rows,separators=(',',':')))
(P/'rowjoint_report.json').write_text(json.dumps(dict(status='PASS_FINITE_JOINT_ROW_SITE_MODEL_ONLY',variables=K,typed_edges=len(edge_subset),iterations=history,full45301_audit_required=True,clock_map52_unchanged=True,added_ff=0,added_cycles=0),indent=1));print('ROW_JOINT_DONE',K,'coupled variables; full45301 audit next',flush=True)
