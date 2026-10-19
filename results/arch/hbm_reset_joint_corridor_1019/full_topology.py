import json,collections,numpy as np,math
from pathlib import Path
O=Path.cwd();L=np.load(O/'compact_corridor_grid.npz')['labels'];ny,nx=L.shape;pitch=10.8;F=L.ravel();S=json.load(open(O/'sinks.json'));V=json.load(open(O/'nativebound_visibility_targets.json'));B=json.load(open(O/'nativebound_visibility_bridges.json'));R=json.load(open(O/'compact_corridor_report.json'));bridge=collections.defaultdict(list)
def idx(xy):return round(xy[1]/pitch)*nx+round(xy[0]/pitch)
for e in B:a,b=map(idx,e['centers_um']);bridge[a].append(b);bridge[b].append(a)
targets=collections.defaultdict(list)
for s,t in zip(S,V):
 x,y=s['xy_um'];good=[]
 for j in range(max(0,math.ceil((y-350)/pitch)),min(ny,math.floor((y+350)/pitch)+1)):
  for i in range(max(0,math.ceil((x-350)/pitch)),min(nx,math.floor((x+350)/pitch)+1)):
   d=abs(i*pitch-x)+abs(j*pitch-y)
   if d<=350 and int(L[j,i])==t['reachable_component']:good.append((d,j*nx+i))
 assert good
 targets[min(good)[1]].append(t['sink_index'])
start=R['source_choice'][1];parent=np.full(nx*ny,-2,dtype=np.int32);parent[start]=-1;q=collections.deque([start]);todo=set(targets);seen=0
while q and todo:
 k=q.popleft();todo.discard(k);seen+=1;j,i=divmod(k,nx)
 for z,ok in [(k-1,i>0),(k+1,i+1<nx),(k-nx,j>0),(k+nx,j+1<ny)]+[(z,True) for z in bridge[k]]:
  if ok and parent[z]==-2 and F[z]!=0:parent[z]=k;q.append(z)
assert not todo
union={start}
for k in targets:
 while k!=-1 and k not in union:union.add(k);k=int(parent[k])
children=collections.defaultdict(list)
for k in union:
 p=int(parent[k])
 if p!=-1:children[p].append(k)
# Keep every used grid point, deliberately finite and uncompressed: no unpriced synthetic long hop.
records=[];depth={start:0};q=collections.deque([start])
while q:
 k=q.popleft();p=int(parent[k]);loc=targets.get(k,[]);copies=math.ceil(len(loc)/24);kid=sorted(children[k]);q.extend(kid)
 for x in kid:depth[x]=depth[k]+1
 records.append({'id':int(k),'center_um':[k%nx*pitch,k//nx*pitch],'parent_id':p,'children':list(map(int,kid)),'sink_indices':loc,'depth_edges':depth[k],'leaf_pairs':copies,'trunk_transparent_loads':2*len(kid)+2*copies,'clock_direct_loads':len(kid)+2+2*copies,'leaf_maxload':min(24,len(loc)),'native_cells':6+4*copies,'PG_terminals':12+8*copies,'row_body_um':[8.424,.54],'total_halo_envelope_um':[10.728,2.844]})
maxload=max(max(v['trunk_transparent_loads'],v['leaf_maxload']) for v in records);maxclock=max(v['clock_direct_loads'] for v in records);leafpairs=sum(v['leaf_pairs'] for v in records);maxdepth=max(v['depth_edges'] for v in records);nativearea=len(records)*1.15182+leafpairs*.84564
report={'status':'FINITE_UNCOMPRESSED_NATIVE_TOPOLOGY_MODEL_ONLY','homes':len(records),'edges':len(records)-1,'sink_count':sum(len(v['sink_indices']) for v in records),'leaf_pairs':leafpairs,'max_trunk_or_leaf_loads':maxload,'max_clock_direct_loads':maxclock,'all_loads_under32':max(maxload,maxclock)<=32,'native_FF':2*(len(records)+leafpairs),'native_BUF':len(records),'native_INV':2*(len(records)+leafpairs),'native_TIEHI':len(records),'native_area_um2':nativearea,'native_PG_MTerm_bindings':sum(v['PG_terminals'] for v in records),'body_total_um2':len(records)*8.424*.54,'maximum_graph_depth':maxdepth,'conditional_max_release_edges':2*(maxdepth+1)+2,'conditional_max_release_ps':(2*(maxdepth+1)+2)*1024,'actual_release_edge':None,'new_legal_rows':None,'actual_PG_OBS_phase':None,'registered_bridge_contact_bound_um':402.6,'native_clock_bridge_bound_um':400.286,'body_inside_previously_checked8p64_envelope':True,'x_site_width':156,'y_rows':2,'minimum_x_home_separation_um':10.8,'total_x_envelope_um':10.728,'all_homes_halo_disjoint_on_grid':True,'compression_performed':False}
for name,obj in [('full_topology_report.json',report),('full_topology.json',records)]:(O/name).write_text(json.dumps(obj,indent=1)+'\n')
print(json.dumps(report,indent=2))
