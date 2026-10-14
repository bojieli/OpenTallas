#!/usr/bin/env python3
"""Independently replay saved route demand, connectivity and exact-pin length diagnostics."""
import argparse,collections,gzip,hashlib,json,sys
from pathlib import Path
import numpy as np

def final_pin_rebind(path,candidate):
 root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'tools/hier_contract'))
 import child_lint
 c=json.load(open(candidate));geometries={}
 for master,m in c['masters'].items():
  evidence=root/m['evidence'];assert hashlib.sha256(evidence.read_bytes()).hexdigest()==m['sha256']
  assert m['kind']=='closed_child_lef','Final screen must not fall back to CTS or planned pins'
  geometries[master]=child_lint.parse_lef(evidence.read_text())
 def point(instance,pin):
  z=c['instances'][instance];m=geometries[z['master']];rect=m['pins'][pin]['rects'][0];x=(rect[1]+rect[3])/2;y=(rect[2]+rect[4])/2
  if z['orient']=='MX':y=m['H']-y
  elif z['orient']=='MY':x=m['W']-x
  else:assert z['orient']=='R0'
  return [x+z['x'],y+z['y']]
 d=json.load(gzip.open(path,'rt'));count=0;expected=set()
 for e in c['connectivity_edges']:
  for sp,dp in zip(e['source_pins'],e['sink_pins']):expected.add((e['cls'],e['source'],sp,e['sink'],dp))
 observed=set()
 for r in d['routes']:
  for q in r['exact_pairs']:
   key=(r['cls'],r['source_instance'],q['source_pin'],r['sink_instance'],q['sink_pin']);assert key not in observed;observed.add(key)
   for direction,instance,pin in [('source',r['source_instance'],q['source_pin']),('sink',r['sink_instance'],q['sink_pin'])]:
    actual=point(instance,pin);assert max(abs(actual[i]-q[direction+'_point_um'][i]) for i in (0,1))<1e-7,(key,direction,actual,q[direction+'_point_um'])
   count+=1
 assert observed==expected,(len(observed),len(expected),list(expected-observed)[:3])
 return dict(actual_final_lef_pin_rebind_pass=True,exact_bit_pairs=count,independent_parser='child_lint.parse_lef',candidate_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),master_final_lef_sha256={m:d['sha256'] for m,d in c['masters'].items()})

def replay(path):
 d=json.load(gzip.open(path,'rt'));C=[np.array(d['capacity_H']),np.array(d['capacity_V'])];U=[np.array(d['escape_demand_H']),np.array(d['escape_demand_V'])];over=[];counts=collections.Counter();worst=0.;normal={'E':(1,0),'W':(-1,0),'N':(0,1),'S':(0,-1)}
 for r in d['routes']:
  graph=collections.defaultdict(list)
  for k,key in enumerate(['H','V']):
   e=np.array(r[key],dtype=int).reshape(-1,2)
   if len(e):np.add.at(U[k],(e[:,0],e[:,1]),r['bits'])
   for y,x in e:
    a=(int(x),int(y));b=(int(x)+(k==0),int(y)+(k==1));graph[a].append(b);graph[b].append(a)
  start,end=tuple(r['source_cell']),tuple(r['sink_cell']);seen=set();cur=start;previous=None
  while cur!=end:
   assert cur not in seen,'Route contains a cycle';seen.add(cur);nxt=[n for n in graph[cur] if n!=previous];assert len(nxt)==1,'Disconnected or branched route';nxt=nxt[0];step=(nxt[0]-cur[0],nxt[1]-cur[1])
   if previous is None:assert sum(x*y for x,y in zip(step,normal[r['source_face']]))>=0
   if nxt==end:assert sum(x*y for x,y in zip(step,normal[r['sink_face']]))<=0
   previous,cur=cur,nxt
  assert len(seen)==len(r['H'])+len(r['V'])
  assert len(r['exact_pairs'])==r['bits'];pp=[]
  for q in r['exact_pairs']:
   length=(len(r['H'])+len(r['V']))*d['gcell_um']+sum(abs(q['source_point_um'][i]-(start[i]+.5)*d['gcell_um'])+abs(q['sink_point_um'][i]-(end[i]+.5)*d['gcell_um']) for i in (0,1));assert abs(length-q['grid_polyline_um'])<.00011;worst=max(worst,length);budget=min(500,q['actual_rc_budget_um']) if q['actual_rc_budget_um'] is not None else 500
   if length>budget:pp.append(q)
  if pp:over.append(dict(cls=r['cls'],source=r['source_instance'],sink=r['sink_instance'],group_bits=r['bits'],bits_over500=len(pp),pairs=pp));counts[r['cls']]+=len(pp)
 full=[float((U[0].sum(axis=0)/C[0].sum(axis=0)).max()),float((U[1].sum(axis=1)/C[1].sum(axis=1)).max())];wins=[]
 for i,axis in enumerate([0,1]):
  a=np.apply_along_axis(lambda x:np.convolve(x,np.ones(5),'valid'),axis,U[i]);b=np.apply_along_axis(lambda x:np.convolve(x,np.ones(5),'valid'),axis,C[i]);wins.append(float((a/b).max()))
 edge=[float((U[i]/C[i]).max()) for i in range(2)];audit=dict(schema='opentallas.hrow_route_replay.v1',artifact_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),groups=len(d['routes']),full_cut_max=full,window54um_cut_max=wins,edge_capacity_max=edge,pass_=max(full+wins)<=.6 and max(edge)<=d.get('edge_limit',1.0),edge_limit=d.get('edge_limit',1.0),full_and_window_cut_limit=.6,all_individual_edges_le_060=max(edge)<=.6,connectivity_and_normal_escapes_pass=True)
 lengths=dict(schema='opentallas.hrow_route_length_diagnostic.v1',groups_over500=len(over),bits_over500=sum(counts.values()),classes_over500=dict(counts),exact_pairs=sum(r['bits'] for r in d['routes']),actual_rc_budget_status='OPEN actual production clock/reset delivery, operating load/slew and routed wire RC budgets unassigned;500um geometric diagnostic only',worst_polyline_um=round(worst,4),over_budget_groups=over)
 return audit,lengths
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('artifact',type=Path);a.add_argument('--out',type=Path,required=True);a.add_argument('--lengths',type=Path,required=True);a.add_argument('--candidate',type=Path);x=a.parse_args();audit,lengths=replay(x.artifact);
 if x.candidate:audit.update(final_pin_rebind(x.artifact,x.candidate))
 x.out.write_text(json.dumps(audit,indent=1)+'\n');x.lengths.write_text(json.dumps(lengths,indent=1)+'\n');print(json.dumps(audit));print({k:v for k,v in lengths.items() if k!='over_budget_groups'})
