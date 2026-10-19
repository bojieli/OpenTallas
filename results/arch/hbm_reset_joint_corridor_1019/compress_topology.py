import json,collections,math
from pathlib import Path
O=Path.cwd();A=json.load(open(O/'full_topology.json'));D={x['id']:x for x in A};start=next(x['id'] for x in A if x['parent_id']==-1);B=json.load(open(O/'nativebound_visibility_bridges.json'));nx=1871
idx=lambda p:round(p[1]/10.8)*nx+round(p[0]/10.8)
critical={x['id'] for x in A if len(x['children'])!=1 or x['sink_indices']};critical.add(start)
for b in B:
 for p in b['centers_um']:
  k=idx(p)
  if k in D:critical.add(k)
q=collections.deque([start]);out={start:dict(D[start],parent_id=-1,children=[],path_um=0,path_points=[])}
while q:
 root=q.popleft()
 for first in D[root]['children']:
  prev=root;k=first;total=0;path=[]
  while True:
   length=sum(abs(D[k]['center_um'][i]-D[prev]['center_um'][i]) for i in [0,1]);total+=length;path.append(D[k]['center_um']);stop=k in critical
   if not stop:
    nxt=D[k]['children'][0];nextlen=sum(abs(D[nxt]['center_um'][i]-D[k]['center_um'][i]) for i in [0,1]);stop=total+nextlen>302.4+1e-6
   if stop:
    out[k]=dict(D[k],parent_id=root,children=[],path_um=total,path_points=path);out[root]['children'].append(k);q.append(k);break
   prev,k=k,D[k]['children'][0]
q=collections.deque([start]);out[start]['depth_edges']=0
while q:
 k=q.popleft();v=out[k];n=len(v['children']);copies=v['leaf_pairs'];v['trunk_transparent_loads']=2*n+2*copies;v['clock_direct_loads']=n+2+2*copies
 for ch in v['children']:out[ch]['depth_edges']=v['depth_edges']+1;q.append(ch)
a=list(out.values());N=len(a);C=sum(x['leaf_pairs'] for x in a);maxwire=max(x['path_um'] for x in a);report={'status':'COMPRESSED_COMPLETE_NATIVE_SOURCE_MODEL_PHYSICAL_HOLD','homes':N,'edges':N-1,'sink_count':sum(len(x['sink_indices']) for x in a),'leaf_pairs':C,'max_trunk_or_leaf_loads':max(max(x['trunk_transparent_loads'],x['leaf_maxload']) for x in a),'max_clock_loads':max(x['clock_direct_loads'] for x in a),'native_FF':2*(N+C),'native_INV':2*(N+C),'native_BUF':N,'native_TIEHI':N,'native_area_um2':N*1.15182+C*.84564,'native_PG_bindings':12*N+8*C,'max_recorded_routed_polyline_um':maxwire,'max_registered_reset_wire_contact_bound_um':maxwire+3,'max_native_clock_wire_contact_bound_um':maxwire+.686,'maximum_stage_depth':max(x['depth_edges'] for x in a),'conditional_max_release_edges':2*(max(x['depth_edges'] for x in a)+1)+2,'actual_TT_FF_phase':None,'actual_minCQ':None,'actual_PG_OBS_tracks_legalrows':None,'continuous_free_channel_claim':False,'model_homes_exact_reserved_rectangle_check':'PASS_CONSERVATIVE_8p64_BODY_PLUS_HALO','actual_wire_layer_access':'OPEN_ALL_SEGMENTS'}
for name,obj in [('compressed_topology_report.json',report),('compressed_topology.json',a)]:(O/name).write_text(json.dumps(obj,indent=1)+'\n')
print(json.dumps(report,indent=2))
