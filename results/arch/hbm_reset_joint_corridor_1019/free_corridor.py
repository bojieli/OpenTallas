import json,math,collections,hashlib
from pathlib import Path
import numpy as np
from scipy.ndimage import label
O=Path.cwd();r=json.load(open(O/'report.json'));p=json.load(open(O/'placements.json'));c=json.load(open(O/'clock_cells.json'));s=json.load(open(O/'sinks.json'));pitch=10.8;half=16.2+1.152;W,H=r['die_um'];nx,ny=math.floor(W/pitch)+1,math.floor(H/pitch)+1
blocked=np.zeros((ny,nx),dtype=np.bool_)
def block(rect):
 x0,y0,x1,y1=rect;i0=max(0,math.floor((x0-half)/pitch)+1);i1=min(nx,math.ceil((x1+half)/pitch));j0=max(0,math.floor((y0-half)/pitch)+1);j1=min(ny,math.ceil((y1+half)/pitch));blocked[j0:j1,i0:i1]=1
for v in p:block([v['x'],v['y'],v['x']+v['w'],v['y']+v['h']])
for v in c:block([v['x'],v['y'],v['x']+1.62,v['y']+.27])
blocked[:math.ceil(half/pitch),:]=1;blocked[-math.ceil(half/pitch):,:]=1;blocked[:,:math.ceil(half/pitch)]=1;blocked[:,-math.ceil(half/pitch):]=1
labels,n=label(~blocked);counts=np.bincount(labels.ravel());counts[0]=0
# This is a free-channel center graph. Wires may overfly cells in a separate future native-layer graph.
def candidates(xy,budget=350):
 x,y=xy;loi=max(0,math.ceil((x-budget)/pitch));hii=min(nx,math.floor((x+budget)/pitch)+1);loj=max(0,math.ceil((y-budget)/pitch));hij=min(ny,math.floor((y+budget)/pitch)+1);out=[]
 for j in range(loj,hij):
  for i in range(loi,hii):
   d=abs(i*pitch-x)+abs(j*pitch-y)
   if d<=budget and labels[j,i]:out.append((round(d,9),j*nx+i,int(labels[j,i])))
 return sorted(out)
source=candidates(r['source']['xy_um']);source_choice=source[0] if source else None;source_label=source_choice[2] if source else None;targets=[]
for k,v in enumerate(s):
 cand=candidates(v['xy_um']);live=[x for x in cand if x[2]==source_label];targets.append({'sink_index':k,'candidate_count':len(cand),'component_ids':sorted({x[2] for x in cand}),'selected':live[0] if live else None,'state':'REACHABLE_FREE_CHANNEL' if live else ('NO_FREE_HOME_IN350' if not cand else 'OTHER_COMPONENT')})
# BFS once, preserving exact parent graph; no reroot/count retry/old allocator.
parent=np.full(nx*ny,-2,dtype=np.int32);start=source_choice[1] if source_choice else None;todo={x['selected'][1] for x in targets if x['selected']};q=collections.deque([start] if start is not None else []);seen=0
if start is not None:parent[start]=-1
while q and todo:
 k=q.popleft();seen+=1;todo.discard(k);j,i=divmod(k,nx)
 for z,ok in [(k-1,i>0),(k+1,i+1<nx),(k-nx,j>0),(k+nx,j+1<ny)]:
  if ok and parent[z]==-2 and labels.ravel()[z]==source_label:parent[z]=k;q.append(z)
union={start} if start is not None else set();pathlengths=[]
for t in targets:
 if not t['selected']:continue
 k=t['selected'][1];ln=0
 while k!=-1:
  union.add(k);k=int(parent[k]);ln+=1
 pathlengths.append(ln-1)
# Each short graph step is a proposed home, not a synthesized block. Compressing requires native pin/branch qualification.
records=[{'grid_index':int(k),'center_um':[int(k)%nx*pitch,int(k)//nx*pitch],'parent_index':int(parent[k])} for k in sorted(union)]
report={'status':'FREE_CHANNEL_MODEL_ONLY','grid_pitch_um':pitch,'native_body_um':32.4,'new_channel_halo_um_each_side':1.152,'inflated_half_um':half,'grid_dimensions':[nx,ny],'grid_nodes':nx*ny,'free_nodes':int((~blocked).sum()),'components':n,'largest_components_cells':sorted(map(int,counts),reverse=True)[:20],'source_candidates':len(source),'source_choice':source_choice,'source_component_size':int(counts[source_label]) if source_label else 0,'reachable_sinks':sum(x['selected'] is not None for x in targets),'unreachable_sinks':sum(x['selected'] is None for x in targets),'no_free_home_sinks':sum(x['state']=='NO_FREE_HOME_IN350' for x in targets),'bfs_visited':seen,'union_candidate_grid_homes':len(union),'max_free_channel_path_um':max(pathlengths,default=0)*pitch,'wire_overfly_graph_evaluated':False,'continuous_geometry_infeasibility_claim':False,'actual_PG_via_track_occupancy':None,'actual_TT_FF_phase':None,'topology_compression_and_native_copy_census':'OPEN'}
for name,obj in [('free_corridor_report.json',report),('free_corridor_targets.json',targets),('free_corridor_union.json',records)]: (O/name).write_text(json.dumps(obj,indent=1)+'\n')
np.savez_compressed(O/'free_corridor_grid.npz',blocked=blocked,labels=labels)
print(json.dumps(report,indent=2))
