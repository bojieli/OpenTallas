#!/usr/bin/env python3
"""One fixed c9 graph-to-site construction; no engine or physical launch.

Uses existing empty MX raw rows and a named common-prefix reservation. Counts,
original graph and logical pad depths are immutable. Native routes, literal PG union,
feeds, reset and clock skew remain explicit obligations.
"""
import bisect,gzip,hashlib,json,math
from collections import deque
from pathlib import Path
from dsrom_noECC_production_context import lef_masters
from dsrom_noECC_hold_station_geometry import pin_rects
from dsrom_c9_selected_clock_access import gap
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_c9_clock_branch_site_binding_20261003'
CUT=ROOT/'results/uarch/dsrom_c9_selected_clock_access_20261003'
OLD=ROOT/'results/uarch/dsrom_R49_raw_physical_union_20261002'
BUF='BUFx4_ASAP7_75t_R';W=378;H=270

def load(p):
 raw=p.read_bytes();raw=gzip.decompress(raw) if p.suffix=='.gz' else raw
 return json.loads(raw)
def lines(p):return [json.loads(s) for s in gzip.decompress(p.read_bytes()).decode().splitlines()]
def dumpgz(p,rows):p.write_bytes(gzip.compress((''.join(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n' for r in rows)).encode(),mtime=0))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(item,name,lef):
 rr=pin_rects(item,lef[item['master']],name);r=max(rr,key=lambda r:(r['bbox_DBU'][2]-r['bbox_DBU'][0])*(r['bbox_DBU'][3]-r['bbox_DBU'][1]));a,b,A,B=r['bbox_DBU']
 return dict(instance=item['instance'],pin=name,point_DBU=[(a+A)/2,(b+B)/2],literal_rectangles=rr)
def literal_cap(a,b,C):
 return min((gap(x['bbox_DBU'][0],x['bbox_DBU'][2],y['bbox_DBU'][0],y['bbox_DBU'][2])*C['M8']+gap(x['bbox_DBU'][1],x['bbox_DBU'][3],y['bbox_DBU'][1],y['bbox_DBU'][3])*C['M9'])/1000 for x in a for y in b)

def cap(a,b,C):return (abs(a[0]-b[0])*C['M8']+abs(a[1]-b[1])*C['M9'])/1000

def topology(branches):
 graph={};D={};pads={}
 for b in branches:graph.setdefault(b['source'],[]).append(b)
 visiting=set()
 def d(n):
  if n not in graph:return 0
  if n in D:return D[n]
  if n in visiting:raise ValueError('source clock graph cycle')
  visiting.add(n);lengths=[b['proposed_relay_BUF']+1+d(b['destination']) for b in graph[n]];D[n]=max(lengths)
  for b,L in zip(graph[n],lengths):pads[(b['net'],b['destination'])]=D[n]-L
  visiting.remove(n);return D[n]
 for n in graph:d(n)
 return pads,D

def free_raw_cells(existing,raw,seats):
 occupied={raw[1]+j*540+270:[] for j in range(seats)}
 for p in existing:
  x,y,X,Y=p['bbox_DBU']
  if y in occupied and y<Y:occupied[y].append((max(raw[0],x),min(raw[2],X)))
 result=[]
 for y,intervals in occupied.items():
  cursor=raw[0];gaps=[]
  for x,X in sorted(set(intervals)):
   if x>cursor:gaps.append((cursor,x))
   cursor=max(cursor,X)
  if cursor<raw[2]:gaps.append((cursor,raw[2]))
  for x,X in gaps:
   xx=math.ceil(x/54)*54
   while xx+W<=X:result.append(dict(bbox_DBU=[xx,y,xx+W,y+H],orientation='MX',domain='raw'));xx+=W
 return result

class Pool:
 def __init__(self,sites,lef):
  self.sites=sites;self.used=set();self.rows={};self.by_domain={}
  for i,p in enumerate(sites):
   q=dict(p,master=BUF,instance=f'site{i}');p['A_rects']=pin_rects(q,lef[BUF],'A');p['A']=pin(q,'A',lef)['point_DBU'];p['Y']=pin(q,'Y',lef)['point_DBU'];key=(p['domain'],p['A'][1]);self.rows.setdefault(key,[]).append((p['A'][0],i))
  for key,items in self.rows.items():items.sort();self.rows[key]=(tuple(p[0] for p in items),tuple(p[1] for p in items))
 def candidates(self,target,source,sink,wire_budget,remaining,C,domain,source_rects):
  options=[]
  for key,(xs,ids) in self.rows.items():
   if key[0]!=domain:continue
   left=wire_budget*1000+500*max(C.values())-abs(key[1]-source[1])*C['M9']
   if left<0:continue
   lo=bisect.bisect_left(xs,source[0]-left/C['M8']-1e-6)
   hi=bisect.bisect_right(xs,source[0]+left/C['M8']+1e-6)
   for j in range(lo,hi):
    ident=ids[j];p=self.sites[ident]
    if literal_cap(source_rects,p['A_rects'],C)<=wire_budget+1e-8 and cap(p['Y'],sink,C)<=remaining*2.88+1e-8:
     options.append((abs(p['A'][0]-target[0])+abs(p['A'][1]-target[1]),key[1],p['A'][0],ident))
  return [v[-1] for v in sorted(options)]
 def allocate(self,target,source,sink,wire_budget,remaining,C,domain=None):
  # Deterministic nearest station, within source-hop and remaining-reach bounds.
  # No buffer count, clock or routing-plane sweep.
  ordered=sorted(self.rows,key=lambda k:(abs(k[1]-target[1]),k));best=None
  for key in ordered:
   if domain is not None and key[0]!=domain:continue
   dy=abs(key[1]-source[1]);left=wire_budget*1000-dy*C['M9']
   if left<0:continue
   xs,ids=self.rows[key];lo=source[0]-left/C['M8'];hi=source[0]+left/C['M8']
   i=bisect.bisect_left(xs,min(hi,max(lo,target[0])))
   for direction,start in ((1,i),(-1,i-1)):
    j=start
    while 0<=j<len(xs) and lo-1e-6<=xs[j]<=hi+1e-6:
     ident=ids[j]
     if ident not in self.used:
      p=self.sites[ident]
      if cap(p['Y'],sink,C)<=remaining*2.88+1e-8:
       score=(abs(p['A'][0]-target[0])+abs(p['A'][1]-target[1]),key[1],p['A'][0],ident)
       if best is None or score<best[0]:best=(score,ident)
       break
     j+=direction
   # Any remaining row has at least this vertical target distance.
   if best is not None and abs(key[1]-target[1])>best[0][0]:break
  if best is None:return None
  self.used.add(best[1]);return self.sites[best[1]]

def route_waypoints(a,b,n,first_budget,C):
 L=abs(b[0]-a[0])+abs(b[1]-a[1]);first=min(L/(n+1),first_budget/max(C.values())*1000)
 def along(d):
  dx=abs(b[0]-a[0]);x=a[0]+math.copysign(min(d,dx),b[0]-a[0]);y=a[1]+math.copysign(max(0,d-dx),b[1]-a[1]);return [x,y]
 return [along(first+j*(L-first)/n) for j in range(n)]

def build():
 for r in load(BASE/'inputs/origins.json'):
  if sha(BASE/'inputs'/r['copy'])!=r['sha256']:raise ValueError('source identity hash mismatch')
 c9=load(CUT/'inputs/model.json');old=load(OLD/'model.json');identity=load(BASE/'inputs/identity.json')
 lef=lef_masters('\n'.join(load(OLD/'inputs/cell_LEF.json.gz').values()));C=c9['restricted_route_family_RC_fF_per_um'];cases={}
 for shard in (0,1):
  s=str(shard);raw=old['physical_shards'][s]['raw_slot_bbox_DBU'];common=identity['common_bbox_DBU'];patch=[common[0],common[1],common[0]+8640,common[1]+5400]
  existing=lines(OLD/f'shard{shard}_cells.jsonl.gz');original={p['instance']:p for p in existing};nets={p['name']:p for p in lines(OLD/f'shard{shard}_clock_nets.jsonl.gz')}
  branches=load(CUT/f'inputs/shard{shard}_clock_branches.json.gz');pads,D=topology(branches)
  if sum(pads.values())!=c9['per_shard_raw_clock_correction_proposals'][shard]['additional_equal_cell_depth_pad_BUF']:raise ValueError('pad census drift')
  sites=free_raw_cells(existing,raw,old['physical_shards'][s]['seats']);raw_pool_count=len(sites)
  if raw_pool_count!=c9['raw_empty_row_correction_site_inventories'][shard]['source_disjoint_free_sites']:raise ValueError('raw free pool drift')
  common_existing=[p['bbox_DBU'] for p in existing if p['role']=='raw_clock_upper']
  for y in range(patch[1],patch[3],270):
   for x in range(patch[0],patch[2]-W+1,W):
    if any(min(x+W,b[2])>max(x,b[0]) and min(y+H,b[3])>max(y,b[1]) for b in common_existing):continue
    sites.append(dict(bbox_DBU=[x,y,x+W,y+H],orientation='R0' if ((y-common[1])//270)%2==0 else 'MX',domain='common'))
  # The single selected successor: exact Maxwell site set and first relays.
  selected=load(BASE/f'inputs/selected_shard{shard}_sites.json.gz')
  sites=[dict(bbox_DBU=v['bbox_DBU'],orientation=v['orientation'],domain=v['home']) for v in selected]
  fixed={(v['branch_net'],v['branch_destination']):i for i,v in enumerate(selected) if v['role']=='first_relay'}
  pool=Pool(sites,lef);tasks=[]
  for b in branches:
   n=b['proposed_relay_BUF']+pads[(b['net'],b['destination'])]
   if n==0:continue
   net=nets[b['net']];sink=next(p for p in net['sinks'] if p['instance']==b['destination']);a=net['source']['point_DBU'];z=sink['point_DBU'];budget=b['first_driver_total_wire_budget_fF']/2/b['source_fanout']
   raw_clamped=[min(raw[2],max(raw[0],a[0])),min(raw[3],max(raw[1],a[1]))];outside=cap(a,raw_clamped,C)>budget
   tasks.append(dict(branch=b,n=n,pads=pads[(b['net'],b['destination'])],a=a,z=z,first_budget=budget,outside=outside,sink=sink,waypoints=route_waypoints(a,z,n,budget,C)))
  tasks.sort(key=lambda t:(not t['outside'],t['first_budget'],t['branch']['source'],t['branch']['destination']))
  assigned=[];failures=[];task_nodes={}
  def add(t,j,source,target,budget,remaining,domain=None):
   p=pool.allocate(target,source,t['z'],budget,remaining,C,domain)
   if p is None:
    failures.append(dict(net=t['branch']['net'],destination=t['branch']['destination'],node=j,domain=domain,source_point_DBU=source,target_point_DBU=target,wire_budget_fF=budget,remaining_nodes=remaining));return None
   b=t['branch'];role='relay' if j<b['proposed_relay_BUF'] else 'depth_pad';name=f"s{shard}.{b['net']}.to.{b['destination']}.{role}{j}"
   q=dict(instance=name,master=BUF,bbox_DBU=p['bbox_DBU'],orientation=p['orientation'],domain=p['domain'],source_net=b['net'],destination=b['destination'],ordinal=j,role=role)
   assigned.append(q);return q
  # Exact first-hop bipartite matching, constrained by both endpoint reach
  # and source fanout budget. Augmenting paths move only fixed-count sites.
  options=[pool.candidates(t['waypoints'][0],t['a'],t['z'],t['first_budget'],t['n'],C,'common' if t['outside'] else 'raw',nets[t['branch']['net']]['source']['literal_rectangles']) for t in tasks]
  owners={};matching={};locked=set()
  for k,t in enumerate(tasks):
   ident=fixed.get((t['branch']['net'],t['branch']['destination']))
   if ident is not None:
    if ident not in options[k]:
     failures.append(dict(net=t['branch']['net'],destination=t['branch']['destination'],node=0,reason='selected_first_hop_fails_combined_first_and_remaining_reach'))
    owners[ident]=k;matching[k]=ident;locked.add(k)
  for k in range(len(options)):
   if k not in locked:options[k]=[i for i in options[k] if i not in owners]

  def augment(k,seen):
   queue=deque([k]);parent={k:None}
   while queue:
    current=queue.popleft()
    for ident in options[current]:
     if ident in seen:continue
     seen.add(ident);prior=owners.get(ident)
     if prior is None:
      while True:
       owners[ident]=current;matching[current]=ident
       if current==k:return True
       current,ident=parent[current]
     if prior not in parent:
      parent[prior]=(current,ident);queue.append(prior)
   return False
  for k in sorted((k for k in range(len(tasks)) if k not in locked),key=lambda k:(len(options[k]),k)):
   if not augment(k,set()):
    t=tasks[k];failures.append(dict(net=t['branch']['net'],destination=t['branch']['destination'],node=0,domain='common' if t['outside'] else 'raw',candidate_sites=len(options[k]),reason='first_hop_maximum_matching_unassigned'))
  pool.used.update(owners)
  for k,t in enumerate(tasks):
   nn=[]
   if k in matching:
    p=pool.sites[matching[k]];b=t['branch'];role='relay' if b['proposed_relay_BUF'] else 'depth_pad'
    q=dict(instance=f"s{shard}.{b['net']}.to.{b['destination']}.{role}0",master=BUF,bbox_DBU=p['bbox_DBU'],orientation=p['orientation'],domain=p['domain'],source_net=b['net'],destination=b['destination'],ordinal=0,role=role)
    assigned.append(q);nn=[q]
   task_nodes[(t['branch']['net'],t['branch']['destination'])]=nn
  edges=[]
  for t in tasks:
   key=(t['branch']['net'],t['branch']['destination']);nn=task_nodes[key]
   if not nn:continue
   for j in range(1,t['n']):
    source=pin(nn[-1],'Y',lef)['point_DBU'];q=add(t,j,source,t['waypoints'][j],2.88,t['n']-j)
    if q is None:break
    nn.append(q)
   source=nets[t['branch']['net']]['source']
   for j,q in enumerate(nn):
    sink=pin(q,'A',lef);edges.append(dict(source=source,sink=sink,branch_net=t['branch']['net'],destination=t['branch']['destination'],ordinal=j,metal_budget_fF=t['first_budget'] if j==0 else 2.88,prescribed_M8_M9_metal_C_fF=cap(source['point_DBU'],sink['point_DBU'],C),native_contact_stubs_coupling_budget_fF=t['first_budget'] if j==0 else 2.88));source=pin(q,'Y',lef)
   if len(nn)==t['n']:
    edges.append(dict(source=source,sink=t['sink'],branch_net=t['branch']['net'],destination=t['branch']['destination'],ordinal=t['n'],metal_budget_fF=2.88,prescribed_M8_M9_metal_C_fF=cap(source['point_DBU'],t['z'],C),native_contact_stubs_coupling_budget_fF=2.88))
  expected=c9['raw_empty_row_correction_site_inventories'][shard]['requested_sites'];outside=sum(t['outside'] for t in tasks)
  dumpgz(BASE/f'shard{shard}_assigned_cells.jsonl.gz',assigned);dumpgz(BASE/f'shard{shard}_assigned_edges.jsonl.gz',edges)
  (BASE/f'shard{shard}_assignment_failures.json').write_text(json.dumps(failures,sort_keys=True,indent=2)+'\n')
  cases[s]=dict(expected_existing_BUF_count=expected,assigned_BUF_count=len(assigned),raw_pool_count=raw_pool_count,raw_new_BUF=sum(p['domain']=='raw' for p in assigned),common_new_BUF=sum(p['domain']=='common' for p in assigned),minimum_outside_first_hops_including_pad_only=outside,
   assignment_failures=len(failures),first_hop_screen='all_literal_pin_rectangle_optimistic_bound_not_fixed_landing',
   optimistic_literal_metal_budget_excess_edges=sum(literal_cap(e['source']['literal_rectangles'],e['sink']['literal_rectangles'],C)>e['metal_budget_fF']+1e-8 for e in edges),
   declared_centroid_metal_budget_excess_edges=sum(e['prescribed_M8_M9_metal_C_fF']>e['metal_budget_fF']+1e-8 for e in edges),
   logical_source_root_cell_depth=max(D.values()),equal_depth_not_skew=True,common_prefix_patch_DBU=patch,common_prefix_patch_reserve_um2=(patch[2]-patch[0])*(patch[3]-patch[1])/1e6,
   common_control_instance_union_not_complete=True,common_prefix_patch_requires_Maxwell_disjoint_ledger=True,
   cell_artifact_sha256=sha(BASE/f'shard{shard}_assigned_cells.jsonl.gz'),edge_artifact_sha256=sha(BASE/f'shard{shard}_assigned_edges.jsonl.gz'),
   native_pin_vias_PG_upfeeds_current_R_C_and_clock_reset_skew_not_qualified=True)
 result=dict(schema='DS_C9_ONE_FIXED_BRANCH_SITE_ASSIGNMENT_V2',candidate=c9['candidate'],source_c9='c9d19ed598077e4a4941c8548273f15deefb8c1a',preserved_selector_bank=c9['selected_selector_clock_construction'],annex_charge_mm2=0,selected_reallocation_source_commit='53dfdf1c9d2bdc4d6a88a24fd785529b1ffad75d',selected_first_relay_sites_locked=True,selected_entire_site_inventory_unchanged=True,hook_source_commit=next(r['commit'] for r in load(BASE/'inputs/origins.json') if r['copy']=='hook_model.json'),expected_total_existing_correction_BUF=68614,added_BUF=0,removed_BUF=0,clock_or_capture_cycle_change=False,physical_build_admitted=False,cases=cases)
 (BASE/'model.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps(cases,indent=2));return result
if __name__=='__main__':build()
