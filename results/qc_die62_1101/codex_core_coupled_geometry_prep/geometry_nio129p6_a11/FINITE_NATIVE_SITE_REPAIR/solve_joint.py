"""Bounded source-only local integer repair on true selected native row sites."""
import gzip,json,math,time,collections
from pathlib import Path
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import coo_matrix
r=Path(__file__).resolve().parent;p=json.load(gzip.open(r/'FINITE_JOINT_PROBLEM.json.gz'));mov=p['movable'];fixed=p['immutable'];ids=sorted(mov);idx={f:i*4 for i,f in enumerate(ids)};W,H=p['geometry']['actual_core_box_um'][2:];cuts={};px,py=.054,.27;halfY=.135;start=time.time();history=[]
fixed_rows=collections.defaultdict(list)
for f,n in fixed.items():fixed_rows[round((n['center_um'][1]-.135)/py)].append((f,n))
def addrow(rows,lo,hi,coef):rows.append((lo,hi,coef))
def xy_expr(f,axis):
 if f in idx:return {idx[f]+axis:(px if axis==0 else py)},(0 if axis==0 else halfY)
 return {},fixed[f]['center_um'][axis]
def linear_xy(rows,terms,lo,hi):
 co=collections.defaultdict(float);const=0
 for f,axis,v in terms:
  e,c=xy_expr(f,axis);const+=v*c
  for k,n in e.items():co[k]+=v*n
 addrow(rows,lo-const,hi-const,dict(co))
def make():
 nv=4*len(ids);lb=[-np.inf]*nv;ub=[np.inf]*nv;integ=[0]*nv;cost=[0.0]*nv;rows=[]
 for f in ids:
  n=mov[f];i=idx[f];w=n['width_um'];lb[i]=math.ceil((w/2)/px);ub[i]=math.floor((W-w/2)/px);lb[i+1]=0;ub[i+1]=math.floor((H-.27)/py);integ[i]=integ[i+1]=1;lb[i+2]=lb[i+3]=0;cost[i+2]=cost[i+3]=1
  lo,hi,vl,vh=n['uv_bounds'];linear_xy(rows,[(f,0,1),(f,1,1)],lo,hi);linear_xy(rows,[(f,0,1),(f,1,-1)],vl,vh)
  target=n.get('prior_center_um') or [(lo+hi+vl+vh)/4,(lo+hi-vl-vh)/4]
  for ax in [0,1]:
   e,c=xy_expr(f,ax);e[i+2+ax]=-1;addrow(rows,-np.inf,target[ax]-c,e)
   e,c=xy_expr(f,ax);e={k:-v for k,v in e.items()};e[i+2+ax]=-1;addrow(rows,-np.inf,-target[ax]+c,e)
 for a,b in p['edges']:
  for sx,sy in [(1,1),(1,-1),(-1,1),(-1,-1)]:linear_xy(rows,[(a,0,sx),(b,0,-sx),(a,1,sy),(b,1,-sy)],-np.inf,399)
 big=2*(W+H)
 for key,(kind,a,b) in cuts.items():
  bools=[]
  for _ in range(4):bools.append(len(lb));lb.append(0);ub.append(1);integ.append(1);cost.append(0)
  if kind=='macro':
   n=mov[a];ox,oy=b['origin_um'];dx,dy=b.get('track_offset_um',[0,0]);ox+=dx;oy+=dy;w,h=b['outline_um'];z=b['halo_um'];end=[ox-z,oy-z,ox+w+z,oy+h+z];pad=[n['width_um']/2,.135]
   for side,(axis,sgn,bound)in enumerate([(0,1,end[0]-pad[0]),(0,-1,-end[2]-pad[0]),(1,1,end[1]-pad[1]),(1,-1,-end[3]-pad[1])]):
    e,c=xy_expr(a,axis);e={k:sgn*v for k,v in e.items()};e[bools[side]]=big;addrow(rows,-np.inf,bound-sgn*c+big,e)
  else:
   na=mov[a];nb=mov.get(b,fixed.get(b));pad=[(na['width_um']+nb['width_um'])/2,.27]
   for side,(axis,sgn)in enumerate([(0,1),(0,-1),(1,1),(1,-1)]):
    ea,ca=xy_expr(a,axis);eb,cb=xy_expr(b,axis);e=collections.defaultdict(float)
    for k,v in ea.items():e[k]+=sgn*v
    for k,v in eb.items():e[k]-=sgn*v
    e[bools[side]]=big;addrow(rows,-np.inf,-pad[axis]-sgn*(ca-cb)+big,dict(e))
  addrow(rows,1,np.inf,{k:1 for k in bools})
 rr=[];cc=[];data=[];los=[];his=[]
 for j,(l,h,c)in enumerate(rows):
  los.append(l);his.append(h)
  for k,v in c.items():rr.append(j);cc.append(k);data.append(v)
 mat=coo_matrix((data,(rr,cc)),shape=(len(rows),len(lb))).tocsc()
 return np.array(cost),np.array(integ),Bounds(np.array(lb),np.array(ub)),LinearConstraint(mat,np.array(los),np.array(his))
def collide(xy):
 new={};pairs=[]
 for f,(x,y)in xy.items():
  n=mov[f];w=n['width_um'];row=round((y-.135)/py)
  for other,b in fixed_rows.get(row,[]):
   a=b['center_um']
   if abs(x-a[0])<(w+b['width_um'])/2-1e-6:pairs.append(('ff',f,other))
  for other,a in xy.items():
   if f>=other:continue
   if abs(y-a[1])<.27-1e-6 and abs(x-a[0])<(w+mov[other]['width_um'])/2-1e-6:pairs.append(('ff',f,other))
  for j,m in enumerate(p['geometry']['macros']):
   ox,oy=m['origin_um'];dx,dy=m.get('track_offset_um',[0,0]);ox+=dx;oy+=dy;mw,mh=m['outline_um'];z=m['halo_um']
   if x+w/2>ox-z+1e-6 and x-w/2<ox+mw+z-1e-6 and y+.135>oy-z+1e-6 and y-.135<oy+mh+z-1e-6:pairs.append(('macro',f,str(j)))
 for kind,a,b in pairs:
  key=(kind,a,b)
  if key not in cuts:new[key]=(kind,a,p['geometry']['macros'][int(b)]if kind=='macro'else b)
 return pairs,new
xy=None;verdict='UNRESOLVED_BOUNDED_LOCAL_MODEL';last=None
for iteration in range(5):
 args=make();res=milp(args[0],integrality=args[1],bounds=args[2],constraints=args[3],options={'time_limit':20,'mip_rel_gap':.1,'threads':2});last=dict(status=int(res.status),message=str(res.message),has_incumbent=res.x is not None)
 if res.x is None:
  history.append(dict(iteration=iteration,cut_count=len(cuts),result=last));break
 xy={f:[float(round(res.x[idx[f]])*px),float(round(res.x[idx[f]+1])*py+.135)]for f in ids};hits,new=collide(xy);history.append(dict(iteration=iteration,cut_count=len(cuts),collisions=len(hits),new_cuts=len(new),result=last));print(history[-1],flush=True)
 if not hits:verdict='FINITE_TYPED_NATIVE_SITE_MODEL_FEASIBLE_SOURCE_ONLY';break
 if not new:break
 cuts.update(new)
summary=dict(status=verdict,movable_count=len(mov),immutable_count=len(fixed),incident_data_edges=len(p['edges']),native_site_um=[px,py],elapsed_s=time.time()-start,iterations=history,last_result=last,holds=p['unqualified'],limits=['Source-only local finite proposal; no native ODB or physical placement','All402/399/149reach budgets retained; no count/function/clock/reset/phase/route credit','Optimality not required or claimed; finite5x20second solve cap'])
(r/'SUMMARY_SOLVE.json').write_text(json.dumps(summary,indent=2)+'\n')
if xy is not None:
 with gzip.open(r/'LOCAL_SITE_CANDIDATE.json.gz','wt')as f:json.dump({'summary':summary,'proposed_centers_um':xy,'movable':mov},f,separators=(',',':'))
print(json.dumps(summary),flush=True)
