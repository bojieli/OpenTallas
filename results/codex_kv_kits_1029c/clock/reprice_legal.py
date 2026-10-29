#!/usr/bin/env python3
"""Evaluate the native R7 model on frozen legal cell origins, before any build.

The tree, masters, sinks, stage counts and datapath are unchanged. Only static
row/site legalization and shortest macro-clear clock-wire geometry are used.
"""
import argparse,json,sys,math,statistics
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('record');p.add_argument('slice');p.add_argument('geo');p.add_argument('libtt');p.add_argument('libff');p.add_argument('out');p.add_argument('--repo',default='/home/ubuntu/OpenTallas');a=p.parse_args()
repo=Path(a.repo);sys.path[:0]=[str(repo/'tools/die_plan'),str(repo/'results/core_lat_r7_1026')]
import core_infra_htree as H
import l0r_r7_model as M
rec=json.load(open(a.record));rec=rec[0] if isinstance(rec,list) else rec;sl=json.load(open(a.slice));coords={k.removeprefix('mp_ck_'):v['centre_um'] for k,v in sl['cell_placements'].items()};masters={k.removeprefix('mp_ck_'):v['master'] for k,v in sl['cell_placements'].items()}
rows=[q.split() for q in Path(a.geo).read_text().splitlines()];sinkpos={};macros=[]
for f in rows:
 if f[:1]==['SINK']:sinkpos[f[4]+'/'+f[5]]=(float(f[1]),float(f[2]),f[4],f[5],f[3])
 if f[:1]==['MACRO']:
  sinkpos[f[1]+'/'+f[7]]=(float(f[8]),float(f[9]),f[1],f[7],'MACRO:'+f[2]);macros.append((f[1],tuple(map(float,f[3:7])),tuple(map(float,f[8:10]))))
base=H.Maze(rec['core'],macros)
class Exact:
 def xy(self,value):
  return tuple(coords[value]) if isinstance(value,str) else tuple(value)
mz=Exact();body=[(r[0]-2.2,r[1]-2.2,r[2]+2.2,r[3]+2.2) for _,r,_ in macros]
def segment_clear(u,v):
 for x0,y0,x1,y1 in body:
  if u[0]==v[0] and x0<u[0]<x1 and min(u[1],v[1])<y1 and max(u[1],v[1])>y0:return False
  if u[1]==v[1] and y0<u[1]<y1 and min(u[0],v[0])<x1 and max(u[0],v[0])>x0:return False
 return True
def route(u,v):
 u,v=tuple(u),tuple(v)
 for q in [(u[0],v[1]),(v[0],u[1])]:
  if segment_clear(u,q) and segment_clear(q,v):return [u,q,v]
 x,y=base.cell(u,node=False),base.cell(v,node=False);path=[u]+[base.xy(t) for t in base.path(x,y)]+[v]
 return path
def length(path):return sum(abs(x[0]-y[0])+abs(x[1]-y[1]) for x,y in zip(path,path[1:]))
nodes=[(n[0],n[1],n[0],masters[n[0]],n[4]) for n in rec['nodes_xy']];names={n[0] for n in nodes};children={n[0]:[] for n in nodes}
for n in nodes:
 if n[1] in children:children[n[1]].append(n[0])
wires=[];land={}
for old in rec['wire_paths']:
 e=old['edge'];count=len(old['segs']);start=e+'_br';reps=[e+'_r'+str(j) for j in range(count-1)];tail=reps[-1] if reps else start
 if e in names:end=coords[e]
 else:
  pts=[coords[n] for n in children[tail]];end=tuple(statistics.median(q[k] for q in pts) for k in (0,1)) if pts else old['paths'][-1][-1]
 chain=[coords[start]]+[coords[n] for n in reps]+[end];paths=[route(x,y) for x,y in zip(chain,chain[1:])];segs=[length(path) for path in paths]
 wires.append(dict(level=old['level'],edge=e,cells=paths,segs=segs))
 if e not in names:land[tail]=(segs[-1],e)
P=dict(mz=mz,nodes=nodes,wires=wires,land=land,leafsinks={n:[sinkpos[s] for s in ss] for n,ss in rec['leaf_sinks'].items()},sinkcap=rec.get('sinkcap',{}))
libnames=sorted(set(masters.values()));libs={'TT':H.lib_cells(a.libtt,libnames),'FF':H.lib_cells(a.libff,libnames)}
r=.5*(1.80365e-2+1.89935e-2)*.8;c=.5*(1.78475e-1+1.64264e-1)*.9
wc={j:rec.get('wire','std') for j in range(1,12)};results,_=M.model_x(P,libs,r,c,wc)
new=dict(rec);new['name']=rec['name']+'_legal';new['pre_legal_model']={k:rec[k] for k in ('TT','FF')};new.update(results);new['nodes_xy']=[(n[0],n[1],list(coords[n[0]]),n[3],n[4]) for n in nodes];new['wire_paths']=[dict(level=w['level'],edge=w['edge'],segs=w['segs'],paths=w['cells']) for w in wires];new['geometry_basis']='frozen legal row/site cell origins, same native R7 NLDM/Elmore chain, no measured timing';new['legal_source_outline_um']=sl['outline_um']
fails=[]
for corner in ('TT','FF'):
 if new[corner]['window']>20:fails.append(corner+' window')
 if new[corner]['leaf_out_slew_max']>80:fails.append(corner+' slew')
badlegs=[]
for w in wires:
 for seg,path in zip(w['segs'],w['cells']):
  u,v=path[0],path[-1];man=abs(u[0]-v[0])+abs(u[1]-v[1])
  if man>1 and seg>1.10*man+1e-6:badlegs.append(dict(edge=w['edge'],um=seg,manhattan=man,path=path))
if badlegs:fails.append('macro detour')
new['legal_geometry_check']={'verdict':'FAIL' if fails else 'PASS','fails':fails,'bad_legs':badlegs,'cells':len(nodes),'sinks':sum(map(len,rec['leaf_sinks'].values()))}
Path(a.out).write_text(json.dumps([new],indent=1)+'\n');print('LEGAL_R7_MODEL',json.dumps({c:new[c] for c in ('TT','FF')}));print('LEGAL_GEOMETRY',new['legal_geometry_check'])
