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

base=make();A=base[3].A.tocsr();lo=base[3].lb;hi=base[3].ub;keep=[i for i in range(A.shape[0])if i>=6*len(ids)or i%6<2];nv=A.shape[1];nr=len(keep);rr=[];cc=[];vv=[];limits=[];labels=[]
for k,oldrow in enumerate(keep):
 if oldrow<6*len(ids):
  f=ids[oldrow//6];label=dict(kind='endpointUV',ff=f,name=mov[f]['name'],axis='u'if oldrow%6==0 else'v',clock_net=mov[f]['clock_net'])
 else:
  e=p['edges'][(oldrow-6*len(ids))//4];label=dict(kind='FFedge',a=e[0],b=e[1],a_name=mov.get(e[0],fixed.get(e[0]))['name'],b_name=mov.get(e[1],fixed.get(e[1]))['name'],a_fixed=e[0]in fixed,b_fixed=e[1]in fixed,a_fixed_xy_um=fixed[e[0]]['center_um']if e[0]in fixed else None,b_fixed_xy_um=fixed[e[1]]['center_um']if e[1]in fixed else None)
 labels.append(label)
 for sign,bound in [(1,hi[oldrow]),(-1,-lo[oldrow])]:
  if not np.isfinite(bound):continue
  row=len(limits)
  for j in range(A.indptr[oldrow],A.indptr[oldrow+1]):
   value=A.data[j]*1000*sign;assert abs(value-round(value))<1e-5,value;rr.append(row);cc.append(A.indices[j]);vv.append(round(value))
  rr.append(row);cc.append(nv+k);vv.append(-1);limits.append(math.floor(bound*1000+1e-5))
mat=coo_matrix((vv,(rr,cc)),shape=(len(limits),nv+nr)).tocsc();integ=np.concatenate([base[1],np.zeros(nr)]);cost=np.concatenate([np.zeros(nv),np.ones(nr)]);bounds=Bounds(np.concatenate([base[2].lb,np.zeros(nr)]),np.concatenate([base[2].ub,np.full(nr,np.inf)]));res=milp(cost,integrality=integ,bounds=bounds,constraints=LinearConstraint(mat,np.full(len(limits),-np.inf),np.array(limits)),options={'time_limit':20,'mip_rel_gap':.01,'threads':2});bad=[]
if res.x is not None:
 for k,slack in enumerate(res.x[nv:]):
  if slack>1e-5:bad.append(dict(slack_DBU=float(slack),**labels[k]))
summary=dict(status='FINITE_INTEGER_DBU_MIN_VIOLATION_DIAGNOSTIC_NOT_ACCEPTANCE',scipy_status=int(res.status),message=str(res.message),has_incumbent=res.x is not None,total_min_violation_DBU=float(res.fun)if res.x is not None else None,nonzero_rows=len(bad),violations=sorted(bad,key=lambda z:-z['slack_DBU']),geometry_and_reach_budgets_unchanged=True,native_SITE_DBU=[54,270],FF_widths_DBU=[1080,1404],row_center_y_DBU=135,interpretation='Any nonzero slack is FAIL. These labeled rows identify frozen context conflicts only; no whole-source impossibility or399/402/149relaxation.',elapsed_s=time.time()-start);(r/'MIN_VIOLATION_DBU.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary),flush=True)
if res.x is not None:
 xy={f:[float(round(res.x[idx[f]])*px),float(round(res.x[idx[f]+1])*py+.135)]for f in ids}
 with gzip.open(r/'MIN_VIOLATION_COORDS_NOT_ACCEPTED.json.gz','wt')as f:json.dump(dict(summary=summary,proposed_centers_um=xy),f,separators=(',',':'))
