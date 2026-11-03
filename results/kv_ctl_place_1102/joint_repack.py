"""Linear geometry PREP; no RTL/physical execution or signoff claim."""
import os;os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1'
import json,sys,collections,math,runpy
from pathlib import Path
O=Path(__file__).resolve().parent
ns=runpy.run_path(str(O/'solve_launch_regions.py'));D=ns['D'];G=ns['G'];anchors=ns['anchors'];caps=ns['captures'];ids=ns['ids'];seq=ns['seq']
TARGET=float(os.environ.get('CTL_LP_REACH','405'));PUBLIC=float(os.environ.get('CTL_LP_PUBLIC','150'));TAG=os.environ.get('CTL_LP_TAG','')
oldpairs=json.loads((O/'far_capture_pairs.json').read_text());expanded='--expand' in sys.argv;all_ff='--all-ff' in sys.argv
if all_ff:moving={i for i,c in D.cells.items() if c[0]=='S'}
elif expanded:
 regions=json.loads((O/'launch_regions.json').read_text())['rows'];moving={ids[x['launch']] for x in regions}|{ids[c['name']] for x in regions for c in x['capture_endpoints']}
else:moving={ids[x[k]] for x in oldpairs for k in ['launch','capture']}
moving={i for i in moving if D.kind(i)=='S'};order=sorted(moving);index={cid:j for j,cid in enumerate(order)};N=len(order)
def upstream(cid):
 todo=[n for n,clock in D.cell_in[cid] if not clock];seen=set();out=set()
 while todo:
  n=todo.pop()
  if n in seen:continue
  seen.add(n);dr=D.nets[n][1]
  if not dr or dr[0]!='i':continue
  if dr[1] in seq:out.add(dr[1])
  else:todo.extend(nn for nn,ck in D.cell_in[dr[1]] if not ck)
 return out
edges=set()
for cid in moving:
 edges.update((cid,x) for x in caps(cid) if x!=cid);edges.update((x,cid) for x in upstream(cid) if x!=cid)
print('JOINT_GRAPH',N,'variables FFs',len(edges),'all incoming/outgoing edges',flush=True)
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
ri=[];ci=[];vs=[];rhs=[]
def add(terms,value):
 row=len(rhs)
 for col,coef in terms:
  if coef:ri.append(row);ci.append(col);vs.append(coef)
 rhs.append(value)
def edge(a,b):
 # Typed memory endpoints use every LEF rectangle corner, as AUTO-GEOM.
 def points(i):
  if i in moving:return [None]
  c=D.cells[i]
  return [G.ctr(c)] if c[0]=='S' else [(c[x],c[y]) for x in [2,4] for y in [3,5]]
 for pa in points(a):
  for pb in points(b):
   for sx,sy in [(1,1),(1,-1),(-1,1),(-1,-1)]:
    terms=[];fixed=0
    if a in moving:terms.extend([(2*index[a],sx),(2*index[a]+1,sy)])
    else:fixed+=sx*pa[0]+sy*pa[1]
    if b in moving:terms.extend([(2*index[b],-sx),(2*index[b]+1,-sy)])
    else:fixed-=sx*pb[0]+sy*pb[1]
    add(terms,TARGET-fixed)
for a,b in edges:edge(a,b)
bounds=[];cost=np.zeros(4*N)
for i,cid in enumerate(order):
 c=D.cells[cid];cw,ch=c[4]-c[2],c[5]-c[3];bounds.extend([(4.32+cw/2,367.2-cw/2),(4.32+ch/2,367.2-ch/2)])
 for p in anchors[cid]:
  for sx,sy in [(1,1),(1,-1),(-1,1),(-1,-1)]:add([(2*i,sx),(2*i+1,sy)],PUBLIC+sx*p['x']+sy*p['y'])
 x,y=G.ctr(c)
 for axis,old in [(0,x),(1,y)]:
  slack=2*N+2*i+axis;add([(2*i+axis,1),(slack,-1)],old);add([(2*i+axis,-1),(slack,-1)],-old);cost[slack]=1000 if anchors[cid] else 1
bounds.extend([(0,None)]*(2*N))
keepouts=[];seen_planes=set()
if os.environ.get('CTL_LP_KEEPOUT'):
 macros=[c for c in D.cells.values() if c[0]=='M']
 for prior_file in os.environ['CTL_LP_KEEPOUT'].split(','):
  prev=json.loads(Path(prior_file).read_text());previous={x['name']:x['new_xy'] for x in prev['points']}
  for i,cid in enumerate(order):
   c=D.cells[cid];cw,ch=c[4]-c[2],c[5]-c[3];x,y=previous[c[6]]
   obstacles=[(m[2]-cw/2-.054,m[3]-ch/2-.054,m[4]+cw/2+.054,m[5]+ch/2+.054,'macro:'+m[6]) for m in macros]
   obstacles.append((181.4-cw/2,181.4-ch/2,190.44+cw/2,190.44+ch/2,'clock/reset entry'))
   for x0,y0,x1,y1,label in obstacles:
    if not(x0<x<x1 and y0<y<y1):continue
    options=[(x-x0,0,1,x0),(x1-x,0,-1,-x1),(y-y0,1,1,y0),(y1-y,1,-1,-y1)]
    poly=[[4.32+cw/2,4.32+ch/2],[367.2-cw/2,4.32+ch/2],[367.2-cw/2,367.2-ch/2],[4.32+cw/2,367.2-ch/2]]
    for pin in anchors[cid]:
     for sx,sy in [(1,1),(1,-1),(-1,1),(-1,-1)]:
      if poly:poly=ns['clip'](poly,sx,sy,PUBLIC+sx*pin['x']+sy*pin['y'])
    valid=[v for v in options if poly and ns['clip'](poly,v[2] if v[1]==0 else 0,v[2] if v[1]==1 else 0,v[3])]
    assert valid,('macro covers public feasible region',c[6],label)
    _,axis,sign,b=min(valid,key=lambda z:z[0]);key=(cid,axis,sign,round(b,6))
    if key not in seen_planes:
     terms=[(2*i+axis,sign)];add(terms,b);keepouts.append(dict(name=c[6],obstacle=label,axis=axis,sign=sign,b=b));seen_planes.add(key)
A=coo_matrix((vs,(ri,ci)),shape=(len(rhs),4*N)).tocsr();print('LP',A.shape,'nonzeros',len(vs),flush=True)
r=linprog(cost,A_ub=A,b_ub=np.array(rhs),bounds=bounds,method='highs',options={'time_limit':20.0})
report=dict(scope=('all actual FFs' if all_ff else 'expanded reachable FFs' if expanded else 'initial failing FFs')+' jointly movable; every reachable incoming/outgoing sequential edge included; current other sequential endpoints fixed; public150/corebounds; minimum weighted public+internal displacement; macro keepouts, overlap, row grid and global pin-p90 are checked after LP, not assumed',success=bool(r.success),status=int(r.status),message=r.message,FFs=N,edges=len(edges),constraints=len(rhs),reach_target=TARGET,public_target=PUBLIC,keepout_planes=len(keepouts))
if r.success:
 points=[];pin_dist=[];moved_pub=[];macro_hits=[]
 macros=[c for c in D.cells.values() if c[0]=='M']
 for i,cid in enumerate(order):
  x,y=r.x[2*i:2*i+2];old=G.ctr(D.cells[cid]);anchor_dist=[dict(pin=p['name'],distance=abs(x-p['x'])+abs(y-p['y'])) for p in anchors[cid]]
  if any(a['distance']>30+1e-6 for a in anchor_dist):moved_pub.append(dict(name=D.cells[cid][6],pins=anchor_dist))
  hit=any(c[2]-4.32<x<c[4]+4.32 and c[3]-4.32<y<c[5]+4.32 for c in macros)
  if hit:macro_hits.append(D.cells[cid][6])
  points.append(dict(name=D.cells[cid][6],old_xy=old,new_xy=[float(x),float(y)],public_anchors=anchor_dist,macro_halo_hit=hit))
 report.update(points=points,public_FFs_over30=len(moved_pub),public_pins_over30=sum(len(x['pins']) for x in moved_pub),macro_halo_hits=len(macro_hits),macro_hit_names=macro_hits)
(O/(('joint_repack_'+TAG+'.json') if TAG else 'joint_repack_all_ff.json' if all_ff else 'joint_repack_expanded.json' if expanded else 'joint_repack.json')).write_text(json.dumps(report,indent=1)+'\n');print({k:v for k,v in report.items() if k not in ['points','macro_hit_names']},flush=True)
