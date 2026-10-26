#!/usr/bin/env python3
"""Coarse street interval connectivity; no station placement or routing claim."""
import argparse, hashlib, json, heapq
from collections import Counter
ap=argparse.ArgumentParser();ap.add_argument('capacity');ap.add_argument('--out',required=True);a=ap.parse_args()
raw=open(a.capacity,'rb').read();d=json.loads(raw)
cols=sorted(d['columns'],key=lambda c:c['x_um']);nodes={};roots={};adj={};boundaries=[]
for ci,c in enumerate(cols):
 ps=sorted((p for p in d['placements'] if abs(p['origin_um'][0]-c['x_um'])<.01),key=lambda p:p['origin_um'][1])
 lo=c['y0_um'];ni=0
 for p in ps:
  hi=p['origin_um'][1];key=f'{ci}:{ni}';nodes[key]=dict(column=ci,x_um=c['x_um'],interval_um=[round(lo,6),round(hi,6)],root_above=p['root']);adj[key]=[];roots[p['root']]=key;ni+=1;lo=hi+p['outline_um'][1]
 key=f'{ci}:{ni}';nodes[key]=dict(column=ci,x_um=c['x_um'],interval_um=[round(lo,6),c['y1_um']],root_above=None);adj[key]=[]
for ci in range(len(cols)-1):
 if ci==10:continue
 edges=[]
 for ka,na in nodes.items():
  if na['column']!=ci:continue
  for kb,nb in nodes.items():
   if nb['column']!=ci+1:continue
   low=max(na['interval_um'][0],nb['interval_um'][0]);high=min(na['interval_um'][1],nb['interval_um'][1]);w=round(high-low,6)
   if w>0:
    adj[ka].append((kb,w));adj[kb].append((ka,w));edges.append(dict(a=ka,b=kb,overlap_um=[low,high],width_um=w))
 nearest=[]
 for ka,na in nodes.items():
  if na['column']!=ci or na['root_above'] is None:continue
  opts=[]
  for kb,nb in nodes.items():
   if nb['column']!=ci+1:continue
   gap=max(0,nb['interval_um'][0]-na['interval_um'][1],na['interval_um'][0]-nb['interval_um'][1])
   opts.append((round(gap,6),kb))
  gap,kb=min(opts);nearest.append(dict(node=ka,root=na['root_above'],nearest_node=kb,vertical_free_interval_gap_um=gap,minimum_manhattan_gap_including_seam_um=round(gap+8.64,6) if gap else 8.64))
 boundaries.append(dict(columns=[ci,ci+1],x_um=[cols[ci]['x_um'],cols[ci+1]['x_um']],positive_edges=edges,nearest_neighbor_streets=nearest))
# widest path, including own street thickness; all inner boundary streets can enter the S14 spine
best={};parent={};heap=[]
for k,n in nodes.items():
 if n['column'] in (10,11):
  w=round(n['interval_um'][1]-n['interval_um'][0],6);best[k]=w;parent[k]=None;heapq.heappush(heap,(-w,k))
while heap:
 neg,k=heapq.heappop(heap);w=-neg
 if w<best[k]-1e-6:continue
 for nxt,cap in adj[k]:
  v=min(w,cap)
  if v>best.get(nxt,0)+1e-6:best[nxt]=v;parent[nxt]=k;heapq.heappush(heap,(-v,nxt))
result=[]
for r,k in sorted(roots.items()):
 path=[];cur=k
 if k in best:
  while cur is not None:path.append(cur);cur=parent[cur]
 result.append(dict(root=r,node=k,column=nodes[k]['column'],street_um=nodes[k]['interval_um'],bottleneck_um=best.get(k,0),path_to_spine=path))
threshold=32.376+2*.432
out=dict(schema='s81.irregular-street-connectivity.v1',capacity_path=a.capacity,capacity_sha256=hashlib.sha256(raw).hexdigest(),script_sha256=hashlib.sha256(open(__file__,'rb').read()).hexdigest(),scope='Optimistic coarse interval graph: column envelopes minus exact frame boxes only. Ignores CFIFO/PQ/HCP/hard blocks, occupancy, track cuts, and finite 500um hop constraints. Does not allow vertical transit through 8.64um intercolumn seams. Connectivity is necessary, not qualification.',x566_horizontal_station_um=[17.256,32.376],clearance_each_um=.432,required_overlap_um=threshold,nodes=nodes,boundaries=boundaries,roots=result,summary=dict(roots=len(result),point_connected=sum(x['bottleneck_um']>0 for x in result),station_connected=sum(x['bottleneck_um']>=threshold for x in result),disconnected_roots=[x['root'] for x in result if not x['bottleneck_um']],connected_bottleneck_histogram=dict(Counter(str(x['bottleneck_um']) for x in result if x['bottleneck_um']))))
open(a.out,'w').write(json.dumps(out,indent=2)+'\n');print(json.dumps(out['summary'],indent=2));print('Required overlap',threshold)
for b in boundaries:
 print('BOUNDARY',b['columns'],'edges',len(b['positive_edges']),'widths',[x['width_um'] for x in b['positive_edges']])
