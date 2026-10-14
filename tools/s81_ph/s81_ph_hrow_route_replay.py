#!/usr/bin/env python3
"""Independently replay saved route demand, connectivity and exact-pin length diagnostics."""
import argparse,collections,gzip,hashlib,json
from pathlib import Path
import numpy as np

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
 edge=[float((U[i]/C[i]).max()) for i in range(2)];audit=dict(schema='opentallas.hrow_route_replay.v1',artifact_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),groups=len(d['routes']),full_cut_max=full,window54um_cut_max=wins,edge_capacity_max=edge,pass_=max(full+wins)<=.6 and max(edge)<=1.0,connectivity_and_normal_escapes_pass=True)
 lengths=dict(schema='opentallas.hrow_route_length_diagnostic.v1',groups_over500=len(over),bits_over500=sum(counts.values()),classes_over500=dict(counts),exact_pairs=sum(r['bits'] for r in d['routes']),actual_rc_budget_status='OPEN final relay ETMs/driver-load wire budgets unassigned;500um diagnostic only',worst_polyline_um=round(worst,4),over_budget_groups=over)
 return audit,lengths
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('artifact',type=Path);a.add_argument('--out',type=Path,required=True);a.add_argument('--lengths',type=Path,required=True);x=a.parse_args();audit,lengths=replay(x.artifact);x.out.write_text(json.dumps(audit,indent=1)+'\n');x.lengths.write_text(json.dumps(lengths,indent=1)+'\n');print(json.dumps(audit));print({k:v for k,v in lengths.items() if k!='over_budget_groups'})
