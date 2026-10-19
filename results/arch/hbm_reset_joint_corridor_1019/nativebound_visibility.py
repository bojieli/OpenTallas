import json,collections,numpy as np
from pathlib import Path
O=Path.cwd();L=np.load(O/'compact_corridor_grid.npz')['labels'];ny,nx=L.shape;pitch=10.8;edges={}
def scan(v,axis,fixed):
 ids=np.flatnonzero(v);d=np.diff(ids);ks=np.flatnonzero((d>1)&(d*pitch<=402))
 for k in ks:
  a,b=int(ids[k]),int(ids[k+1]);ca,cb=int(v[a]),int(v[b]);
  if ca==cb:continue
  xy1=[a*pitch,fixed*pitch] if axis==0 else [fixed*pitch,a*pitch];xy2=[b*pitch,fixed*pitch] if axis==0 else [fixed*pitch,b*pitch];key=tuple(sorted([ca,cb]));e={'components':[ca,cb],'centers_um':[xy1,xy2],'span_center_um':(b-a)*pitch,'native_clock_span_upper_um':(b-a)*pitch+.686,'reset_pin_span_upper_um':(b-a)*pitch+3,'wire_layer_OBS_clear':None,'actual_PG_track_clear':None}
  if key not in edges or e['span_center_um']<edges[key]['span_center_um']:edges[key]=e
for j in range(ny):scan(L[j],0,j)
for i in range(nx):scan(L[:,i],1,i)
adj=collections.defaultdict(list)
for k,e in edges.items():a,b=k;adj[a].append(b);adj[b].append(a)
start=json.load(open(O/'compact_corridor_report.json'))['source_choice'][2];parents={start:None};q=collections.deque([start])
while q:
 a=q.popleft()
 for b in sorted(adj[a]):
  if b not in parents:parents[b]=a;q.append(b)
T=json.load(open(O/'compact_corridor_targets.json'));targets=[];used=set()
for t in T:
 good=sorted(set(t['component_ids'])&set(parents));targets.append({'sink_index':t['sink_index'],'reachable_component':good[0] if good else None,'wire_OBS_PG_qualification':'OPEN'})
 if good:
  x=good[0]
  while parents[x] is not None:used.add(tuple(sorted((x,parents[x]))));x=parents[x]
report={'status':'CONDITIONAL_WIRE_OVERFLY_VISIBILITY_MODEL_NO_NATIVE_ROUTING_CLAIM','registered_span_budget_um':405,'native_reset_contact_allowance_um':3,'derived_center_span_bound_um':402,'components':int(L.max()),'potential_component_edges':len(edges),'source_component':start,'source_reachable_components':len(parents),'reachable_sinks':sum(x['reachable_component'] is not None for x in targets),'unreachable_sinks':sum(x['reachable_component'] is None for x in targets),'required_component_bridges':len(used),'max_bridge_center_um':max((edges[k]['span_center_um'] for k in used),default=0),'all_bridge_native_contact_upper_under405':all(edges[k]['reset_pin_span_upper_um']<=405 and edges[k]['native_clock_span_upper_um']<=405 for k in used),'native_layer_OBS_clear':None,'actual_PG_channel_clear':None,'legal_std_rows_exist':None,'min_CQ_phase_electrical':None,'free_channel_path_compression_and_fanout_copies':'REQUIRED_BEFORE_PROTOTYPE'}
for name,obj in [('nativebound_visibility_report.json',report),('nativebound_visibility_targets.json',targets),('nativebound_visibility_bridges.json',[edges[k] for k in sorted(used)])]:(O/name).write_text(json.dumps(obj,indent=1)+'\n')
print(json.dumps(report,indent=2))
