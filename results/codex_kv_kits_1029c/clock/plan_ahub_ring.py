#!/usr/bin/env python3
"""Use the existing native clock family API with actual fixed footprint node keep-outs.

This is plan-stage geometry; no timing measurement or physical retry is read.
All original occupied footprints remain unavailable to new clock driver cells.
"""
import argparse,json,sys,math,importlib.util,types
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--family',required=True);p.add_argument('--core',required=True);p.add_argument('--kit',required=True);p.add_argument('--work',required=True);p.add_argument('--libtt',required=True);p.add_argument('--libff',required=True);a=p.parse_args()
repo=Path(a.repo);sys.path.insert(0,str(repo/'tools/die_plan'));sp=importlib.util.spec_from_file_location('native_core_family',repo/'tools/die_plan/core_family_slice.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
w=Path(a.work)/a.core;sites=w/'sites.txt';rect=[];hard=[]
for ln in sites.read_text().splitlines():
 f=ln.split()
 if f[:1]==['FIXED']:
  x0,y0,x1,y1=map(float,f[3:7])
  # Macro bodies+halo already enter the native maze from the actual source census.
  if y1-y0>.40:
   hard.append((x0-2.2,y0-2.2,x1+2.2,y1+2.2));continue
  rect.append((x0-1.62/2-.108,y0-.27/2-.054,x1+1.62/2+.108,y1+.27/2+.054))
old=m.H.Maze.__init__
def init(self,core,macros,G=.54,halo=2.2,keepout=()):
 old(self,core,macros,G=G,halo=halo,keepout=keepout)
 for x0,y0,x1,y1 in hard:
  lo=max(0,math.ceil((x0-core[0])/G));hi=min(self.NX,math.floor((x1-core[0])/G))
  ly=max(0,math.ceil((y0-core[1])/G));hy=min(self.NY,math.floor((y1-core[1])/G))
  for i in range(lo,hi+1):
   for j in range(ly,hy+1):self.B[i][j]=True;self.K[i][j]=True
 for x0,y0,x1,y1 in rect:
  lo=max(0,math.ceil((x0-core[0])/G));hi=min(self.NX,math.floor((x1-core[0])/G))
  ly=max(0,math.ceil((y0-core[1])/G));hy=min(self.NY,math.floor((y1-core[1])/G))
  for i in range(lo,hi+1):
   for j in range(ly,hy+1):self.K[i][j]=True
m.H.Maze.__init__=init
native_plan=m.plan
def repair_waypoints(geo,family,libtt,libff,name,trunk_cal=None):
 rec=native_plan(geo,family,libtt,libff,name,trunk_cal=trunk_cal)
 P,libs,r,c,wc=m._PLANS[name];mz=P['mz'];repairs=[]
 for wire in P['wires']:
  bad=[]
  for j,(length,path) in enumerate(zip(wire['segs'],wire['cells'])):
   x,y=mz.xy(path[0]);xx,yy=mz.xy(path[-1]);man=abs(x-xx)+abs(y-yy)
   if man>1 and length>1.10*man+1e-6:bad.append(j)
  if not bad:continue
  # Existing repeater stages only. Move a waypoint to a free clock site so
  # BOTH adjacent physical legs are shortest routes with no macro detour.
  j=bad[0];idx=min(j,len(wire['segs'])-2)
  if idx<0:continue
  node=wire['edge']+'_r'+str(idx)
  oldpos=next((n[2] for n in P['nodes'] if n[0]==node),None)
  if oldpos is None:continue
  a=wire['cells'][idx][0];b=wire['cells'][idx+1][-1]
  da,db=mz.bfs(a),mz.bfs(b);ax,ay=mz.xy(a);bx,by=mz.xy(b)
  candidates=[]
  for i in range(mz.NX+1):
   for k in range(mz.NY+1):
    if not mz.site_ok(i,k) or da[i][k]<0 or db[i][k]<0:continue
    x,y=mz.xy((i,k));la,lb=da[i][k]*mz.G,db[i][k]*mz.G
    if max(la,lb)>family.get('smax',70)+1e-6:continue
    ma,mb=abs(x-ax)+abs(y-ay),abs(x-bx)+abs(y-by)
    if la>1.10*ma+1e-6 or lb>1.10*mb+1e-6:continue
    candidates.append((la+lb,abs(la-lb),i,k,la,lb))
  chosen=None
  for _,_,i,k,la,lb in sorted(candidates):
   x,y=mz.xy((i,k))
   if any(n[0]!=node and abs(mz.xy(n[2])[0]-x)<1.728 and abs(mz.xy(n[2])[1]-y)<.324 for n in P['nodes']):continue
   chosen=(i,k,la,lb);break
  if chosen is None:continue
  i,k,la,lb=chosen;point=(i,k)
  P['nodes']=[(n[0],n[1],point if n[0]==node else n[2],n[3],n[4]) for n in P['nodes']]
  wire['segs'][idx:idx+2]=[la,lb]
  wire['cells'][idx:idx+2]=[mz.path(a,point),mz.path(point,b)]
  repairs.append(dict(node=node,old_xy_um=mz.xy(oldpos),xy_um=mz.xy(point),leg_um=[la,lb],stages_added=0))
 if repairs:
  def corners(path):
   points=[mz.xy(q) for q in path];out=[points[0]]
   for j in range(1,len(points)-1):
    if (points[j][0]-out[-1][0])*(points[j+1][1]-points[j][1]) != (points[j][1]-out[-1][1])*(points[j+1][0]-points[j][0]):out.append(points[j])
   return out+[points[-1]]
  rec['nodes_xy']=[(n[0],n[1],mz.xy(n[2]),n[3],n[4]) for n in P['nodes']]
  rec['wire_paths']=[dict(level=q['level'],edge=q['edge'],segs=[round(x,2) for x in q['segs']],paths=[corners(path) for path in q['cells']]) for q in P['wires']]
  result,_=m.M7.model_x(P,libs,r,c,wc);rec['pre_waypoint_model']={q:rec[q] for q in ('TT','FF')};rec.update(result)
  rec['routing_waypoint_repair']=repairs
 return rec
m.plan=repair_waypoints
# The die's real canvas comes from its ODB, never len(cut-row fragments).
run_subprocess=m.subprocess.run
def with_outline(cmd,*args,**kwargs):
 if isinstance(cmd,list) and len(cmd)>1 and Path(str(cmd[1])).name=='core_plan_to_infra.py' and '--outline' not in cmd:
  line=next(q.split() for q in (w/'geo.txt').read_text().splitlines() if q.startswith('DIE '));x0,y0,x1,y1=map(float,line[1:5]);cmd=cmd+['--outline',str(x1-x0)+','+str(y1-y0)]
 return run_subprocess(cmd,*args,**kwargs)
m.subprocess.run=with_outline
fam=json.loads(Path(a.family).read_text());args=types.SimpleNamespace(libtt=a.libtt,libff=a.libff,trunk_cal=None,replan_cal=None,fit=None,libdir=None,d1_steps=60)
(w/'occupied_geometry_policy.json').write_text(json.dumps({'fixed_footprints':len(rect),'all_actual_hard_bodies_full_wire_obstacles':len(hard),'clock_master_width_um':1.62,'clock_master_height_um':.27,'horizontal_margin_um':.108,'vertical_margin_um':.054,'timing_measurements_read':False,'cycles_added':0},indent=1)+'\n')
f=fam['families'][0]
if 'native_ring_islands' not in f:raise SystemExit('explicit source-derived island packet required')
islands=json.loads(Path(f['native_ring_islands']).read_text())['islands']
def corridor_ring(geo,sp,smax,keepout=()):
 return m.H.plan_ring(geo,islands,[6,6,6,6],leaf_n=4,smax=smax,keepout=keepout,hub_ring=True)
m.H.plan=corridor_ring
r=m.run_core(fam,a.core,a.kit,a.work,args)
print('OCCUPIED_CLOCK_PLAN',json.dumps(r))
