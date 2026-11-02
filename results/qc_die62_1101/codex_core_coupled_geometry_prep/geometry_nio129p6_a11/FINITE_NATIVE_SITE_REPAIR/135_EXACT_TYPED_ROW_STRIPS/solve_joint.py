"""Bounded source-only local integer repair on true selected native row sites."""
import gzip,json,math,time,collections
from pathlib import Path
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import coo_matrix
r=Path(__file__).resolve().parent;p=json.load(gzip.open(r/'FINITE_JOINT_PROBLEM.json.gz'));mov=p['movable'];fixed=p['immutable'];ids=sorted(mov);idx={f:i*4 for i,f in enumerate(ids)};W,H=p['geometry']['actual_core_box_um'][2:];cuts={};px,py=.054,.27;halfY=.135;start=time.time();history=[]
fixed_rows=collections.defaultdict(list)
for f,n in fixed.items():fixed_rows[round((n['center_um'][1]-.135)/py)].append((f,n))
# Exact forbidden native-center intervals, dilated by each movable master width.
blocked={}
for wd in sorted({round(n['width_um']*1000)for n in mov.values()}):
 byrow={}
 for row,items in fixed_rows.items():
  intervals=[]
  for f,n in items:
   cx=round(n['center_um'][0]*1000);rad=(round(n['width_um']*1000)+wd)//2;lo=(cx-rad)//54+1;hi=-(-(cx+rad)//54)-1;intervals.append((lo,hi))
  merged=[]
  for lo,hi in sorted(intervals):
   if merged and lo<=merged[-1][1]+1:merged[-1]=(merged[-1][0],max(hi,merged[-1][1]))
   else:merged.append((lo,hi))
  byrow[row]=merged
 blocked[wd]=byrow

def fixed_strip(f,x,y):
 col=round(x/px);row=round((y-.135)/py);tab=blocked[round(mov[f]['width_um']*1000)]
 def interval(rr):
  return next(((a,b)for a,b in tab.get(rr,[])if a<=col<=b),None)
 z=interval(row)
 if z is None:raise ValueError(('collision lacks exact forbidden center interval',f,x,y))
 lo,hi=z;rl=rh=row;best=[lo,hi,rl,rh];score=hi-lo+1;down=up=True
 for _ in range(10000):
  changed=False
  for direction in [-1,1]:
   if not(down if direction==-1 else up):continue
   rr=rl-1 if direction==-1 else rh+1;zz=interval(rr)
   if zz is None:
    if direction==-1:down=False
    else:up=False
    continue
   lo=max(lo,zz[0]);hi=min(hi,zz[1])
   if direction==-1:rl=rr
   else:rh=rr
   area=(hi-lo+1)*(rh-rl+1)
   if area>score:best=[lo,hi,rl,rh];score=area
   changed=True
  if not changed:break
 return dict(cols_rows=best,width_DBU=round(mov[f]['width_um']*1000),basis='Every included nativecenter is blocked by actual immutable typed FF metal bbox; intersection across contiguous rows. No synthetic keepout or reach change.')

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
  elif kind=='fixed_strip':
   cl,ch,rl,rh=b['cols_rows'];bounds4=[(0,1,(cl-1)*px),(0,-1,-(ch+1)*px),(1,1,.135+(rl-1)*py),(1,-1,-(.135+(rh+1)*py))]
   for side,(axis,sgn,bound)in enumerate(bounds4):
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
  if kind=='ff'and b in fixed:
   z=fixed_strip(a,*xy[a]);key=('fixed_strip',a,tuple(z['cols_rows']))
   if key not in cuts:new[key]=('fixed_strip',a,z)
  else:
   key=(kind,a,b)
   if key not in cuts:new[key]=(kind,a,p['geometry']['macros'][int(b)]if kind=='macro'else b)
 return pairs,new
seed=json.load(open(r/'SEED_EXACT_OCCUPANCY_CUTS.json'))
for item in seed:
 kind,a,b=item['kind'],item['ff'],item['constraint'];assert a in mov
 if kind=='fixed_strip':key=(kind,a,tuple(b['cols_rows']))
 elif kind=='macro':key=(kind,a,str(next(j for j,m in enumerate(p['geometry']['macros'])if m['inst']==b['inst'])))
 elif kind=='ff':key=(kind,a,b)
 else:raise ValueError(kind)
 cuts[key]=(kind,a,b)
print('EXACT_SAVED_OCCUPANCY_CUTS',len(cuts),flush=True)
xy=None;verdict='UNRESOLVED_BOUNDED_LOCAL_MODEL';last=None
for iteration in range(5):
 args=make();dbu_constraint=LinearConstraint(args[3].A*1000,np.ceil(args[3].lb*1000-1e-5),np.floor(args[3].ub*1000+1e-5));res=milp(args[0],integrality=args[1],bounds=args[2],constraints=dbu_constraint,options={'time_limit':20,'mip_rel_gap':.1,'threads':2});last=dict(status=int(res.status),message=str(res.message),has_incumbent=res.x is not None)
 if res.x is None:
  history.append(dict(iteration=iteration,cut_count=len(cuts),result=last));break
 xy={f:[float(round(res.x[idx[f]])*px),float(round(res.x[idx[f]+1])*py+.135)]for f in ids};hits,new=collide(xy);history.append(dict(iteration=iteration,cut_count=len(cuts),collisions=len(hits),new_cuts=len(new),result=last));print(history[-1],flush=True)
 if not hits:verdict='FINITE_TYPED_NATIVE_SITE_MODEL_FEASIBLE_SOURCE_ONLY';break
 if not new:break
 cuts.update(new)
summary=dict(status=verdict,movable_count=len(mov),immutable_count=len(fixed),incident_data_edges=len(p['edges']),native_site_um=[px,py],elapsed_s=time.time()-start,iterations=history,last_result=last,holds=p['unqualified'],limits=['Source-only local finite proposal; no native ODB or physical placement','All402/399/149reach budgets retained; no count/function/clock/reset/phase/route credit','ExactintegerDBU coefficientscaling and135variable conflict-only expansion; no slacks accepted','Optimality not required or claimed; finite5x20second solve cap'])
(r/'EXACT_OCCUPANCY_CUTS.json').write_text(json.dumps([dict(kind=k[0],ff=k[1],constraint=v[2])for k,v in cuts.items()],indent=2)+'\n')
(r/'SUMMARY_SOLVE.json').write_text(json.dumps(summary,indent=2)+'\n')
if xy is not None:
 with gzip.open(r/'LOCAL_SITE_CANDIDATE.json.gz','wt')as f:json.dump({'summary':summary,'proposed_centers_um':xy,'movable':mov},f,separators=(',',':'))
print(json.dumps(summary),flush=True)
