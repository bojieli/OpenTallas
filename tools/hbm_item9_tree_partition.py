#!/usr/bin/env python3
"""Map actual kept/mapped full32 gates to finite source-local caller allocations.

No source transformation, synthesis, timing rerun, placeholder pins or free
channel capacity. Bulk per-cell bindings stay on the compute host.
"""
import hashlib,json,re,sys
from collections import Counter,deque
from pathlib import Path
loads,allocation,out=map(Path,sys.argv[1:4]);payload_only='--payload-affinity' in sys.argv[4:];receiver_affinity='--receiver-affinity' in sys.argv[4:];assert not out.exists()
s=json.loads((loads/'summary.json').read_text());a=json.loads(allocation.read_text())
assert s['actual_library_pin_loads'] and not s['physical_qualified']
raw=loads/'mapped.json';assert hashlib.sha256(raw.read_bytes()).hexdigest()==s['artifacts']['mapped.json']['sha256']
modules=json.loads(raw.read_text())['modules']
top=next(name for name in modules if name.startswith('ot_gpu_coll_item9_context32'))
net=modules[top]
lib=json.loads((loads/'library_input_caps_ff.json').read_text())['SS']
regions={x['caller']:x['proposed_local_register_bbox_um'] for x in a['local_caller_proposal']}
assert set(regions)==set(range(32))
seed={};ff=[];comb=[];drivers={};receivers={}
for name,c in net['cells'].items():
 typ=c['type']
 if typ=='$scopeinfo':assert not c['connections'];continue
 assert typ in lib,(typ,name)
 ins={b for p,bs in c['connections'].items() if p in lib[typ] for b in bs if isinstance(b,int)}
 outs={b for p,bs in c['connections'].items() if p not in lib[typ] for b in bs if isinstance(b,int)}
 assert outs,(name,typ)
 m=re.match(r'g_on\.g_sm_caller\[(\d+)\]\.',name)
 if typ.startswith('DFF'):
  payload=bool(m and re.match(r'g_on\.g_sm_caller\[\d+\]\.(?:c_data|vr)\[',name))
  mask=1<<int(m[1]) if m and (not payload_only or payload) else 0
  destination=1<<int(m[1]) if m else 1<<32
  for bit in ins:receivers[bit]=receivers.get(bit,0)|destination
  for bit in outs:seed[bit]=mask
  ff.append((name,mask,typ));continue
 idx=len(comb);comb.append((name,ins,outs,typ))
 for bit in outs:assert bit not in drivers;drivers[bit]=idx
# Actual primary caller-side cut inputs also retain their source-local affinity.
for name,p in net['ports'].items():
 if p['direction']!='input':continue
 stride=({'issue_va':4096} if payload_only else {'issue_va':4096,'issue_count':8,'issue':1,'issue_mode':1}).get(name)
 for j,bit in enumerate(p['bits']):
  if isinstance(bit,int):seed[bit]=(1<<(j//stride)) if stride else 0
fanout=[[] for _ in comb];remaining=[]
for idx,(_,ins,_,_) in enumerate(comb):
 deps={drivers[b] for b in ins if b in drivers};remaining.append(len(deps))
 for d in deps:fanout[d].append(idx)
queue=deque(i for i,n in enumerate(remaining) if n==0);masks=[0]*len(comb);visited=0;order=[]
while queue:
 i=queue.popleft();_,ins,outs,_=comb[i];mask=0
 for bit in ins:mask|=seed.get(bit,0)
 masks[i]=mask
 for bit in outs:seed[bit]=mask
 visited+=1
 order.append(i)
 for j in fanout[i]:
  remaining[j]-=1
  if remaining[j]==0:queue.append(j)
assert visited==len(comb),('unresolved combinational dependencies',len(comb)-visited)
if receiver_affinity:
 for name,p in net['ports'].items():
  if p['direction']!='output':continue
  stride={'caller_idle':1,'caller_done':1,'caller_vr':4096}.get(name)
  for j,bit in enumerate(p['bits']):
   if isinstance(bit,int):receivers[bit]=receivers.get(bit,0)|(1<<(j//stride) if stride else 1<<32)
 for i in reversed(order):
  _,ins,outs,_=comb[i];destination=0
  for bit in outs:destination|=receivers.get(bit,0)
  for bit in ins:receivers[bit]=receivers.get(bit,0)|destination
out.mkdir(parents=True);groups={};counts=Counter();masters={}
def place_group(mask):
 if mask==0 or mask==(1<<32)-1:return 'hb_coll'
 callers=[s for s in range(32) if mask&(1<<s)]
 # Intermediate trees remain in accepted caller space, at the nearest allocated
 # box to their actual source centroid; this is an affinity, not a corridor claim.
 centers={s:((regions[s][0]+regions[s][2])/2,(regions[s][1]+regions[s][3])/2) for s in callers}
 x=sum(p[0] for p in centers.values())/len(callers);y=sum(p[1] for p in centers.values())/len(callers)
 s=min(callers,key=lambda k:abs(centers[k][0]-x)+abs(centers[k][1]-y))
 return 'caller_'+str(s)
control_groups={}
if receiver_affinity:
 for i,(name,ins,outs,typ) in enumerate(comb):
  if masks[i]!=0:continue
  destination=0
  for bit in outs:destination|=receivers.get(bit,0)
  if not destination&(1<<32):control_groups[name]=place_group(destination)
with (out/'actual_cell_affinity.jsonl').open('w') as f:
 for name,mask,typ in ff+[(c[0],masks[i],c[3]) for i,c in enumerate(comb)]:
  group=place_group(mask)
  if name in control_groups:group=control_groups[name]
  local=re.match(r'g_on\.g_sm_caller\[(\d+)\]\.',name)
  if payload_only and mask==0 and local:group='caller_'+local[1]
  counts[group]+=1;masters.setdefault(group,Counter())[typ]+=1
  groups.setdefault(str(mask),Counter())[group]+=1
  f.write(json.dumps(dict(instance=name,master=typ,source_caller_mask=mask,allocation=group))+'\n')
summary=dict(source_mapped_sha256=s['mapped_sha256'],mapped_JSON_sha256=s['artifacts']['mapped.json']['sha256'],allocation_sha256=hashlib.sha256(allocation.read_bytes()).hexdigest(),
 mapped_flops=len(ff),mapped_comb_cells=len(comb),all_comb_dependencies_resolved=True,
 region_cell_counts=counts,region_master_counts=masters,actual_source_mask_affinities={k:dict(v) for k,v in groups.items()},
 local_allocations=regions,endpoint_allocation=a['baseline_endpoint_mux']['proposed_child_bbox_um'],
 primary_caller_inputs_are_source_local=True,distributed_request_bits=131072,shared_response_bits=4096,shared_response_real_receivers=32,
 actual_intermediate_gate_affinities=True,payload_affinity_separate_from_shared_control=payload_only,
 zero_origin_control_buffers_use_actual_receiver_affinity=receiver_affinity,
 allocated_free_corridor_tracks=0,physical_pin_and_other_claim_route_binding=False,
 source_new_cycles=0,propagated_CLK_and_wire_RC_measured=False,physical_qualified=False,adopted=False,
 bulk_binding=str(out/'actual_cell_affinity.jsonl'),bulk_binding_sha256=hashlib.sha256((out/'actual_cell_affinity.jsonl').read_bytes()).hexdigest())
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(dict(mapped_flops=len(ff),mapped_comb_cells=len(comb),region_cell_counts=counts)))
