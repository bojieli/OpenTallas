import json,numpy as np,collections
from pathlib import Path
O=Path.cwd();g=np.load(O/'free_corridor_grid.npz');L=g['labels'];T=json.load(open(O/'free_corridor_targets.json'));r=json.load(open(O/'report.json'));pitch=10.8;x,y=r['source']['xy_um'];source=collections.defaultdict(list)
for j in range(max(0,int((y-350)/pitch)),min(L.shape[0],int((y+350)/pitch)+1)):
 for i in range(max(0,int((x-350)/pitch)),min(L.shape[1],int((x+350)/pitch)+1)):
  d=abs(i*pitch-x)+abs(j*pitch-y)
  if d<=350 and L[j,i]:source[int(L[j,i])].append([d,i*pitch,j*pitch])
rows=[]
for k,v in source.items():rows.append({'component':k,'source_home_candidates':len(v),'nearest_source_home':min(v),'covered_sinks':[t['sink_index'] for t in T if k in t['component_ids']]})
rows.sort(key=lambda x:(-len(x['covered_sinks']),x['nearest_source_home'][0],x['component']));union=sorted({i for x in rows for i in x['covered_sinks']})
out={'status':'DETERMINISTIC_ALL_SOURCE_COMPONENT_QUERY_NO_PLACEMENT','source_accessible_components':len(rows),'best_single_component_sink_coverage':len(rows[0]['covered_sinks']) if rows else 0,'all_source_components_union_sink_coverage':len(union),'union_not_single_root_or_fanout_proof':True,'source_components':rows,'no_source_component_sink_indices':[i for i in range(810) if i not in union]}
(O/'source_component_coverage.json').write_text(json.dumps(out,indent=1)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ['source_components','no_source_component_sink_indices']},indent=2))
