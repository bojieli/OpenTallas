import json,math
from pathlib import Path
from collections import Counter
import core_infra as CI,core_infra_plan as CP,core_infra_wire as CW
from core_infra_search import Model
p=Path('.');data=json.load(open('input.json'));sl=json.load(open('entry_candidate.json'));previous=json.load(open('report.json'));routing=previous['routing_model'];tech=CP.read_technology('technology.tsv');sl,legal=CP.legalize_slice(sl,tech)
model=Model(sl,data['libraries'],data['points'],data['caps'],0,0,input_slew_ps=0,routing_model=routing);res=model.evaluate([n['master'] for n in sl['core_tree']['nodes']]);prediction=CP.predict_tree(sl,data['libraries'],data['points'],data['caps'],0,0,input_slew_ps=0,routing_model=routing)
plan=CI.compile_slice(sl);cells={c['name']:c for c in plan['cells']};children={n['name']:[] for n in plan['core_tree']['nodes']};leaf_sinks={}
for n in plan['core_tree']['nodes']:
 if n['parent'] in children:children[n['parent']].append(n['name'])
for leaf in plan['core_tree']['leaves']:leaf_sinks.setdefault(leaf['node'],[]).extend(leaf['sinks'])
route_lines=[];demand=Counter();gcell=10.8
for n in plan['core_tree']['nodes']:
 name=n['name'];point=cells[name]['xy_um'];points=[point]+[cells[q]['xy_um'] for q in children[name]]+[data['points'][q] for q in leaf_sinks.get(name,[])];profile=routing.get('nodes',{}).get(name,routing['nonleaf' if children[name] else 'leaf']);rc=CW.rooted_rc(points,[0.]*(len(points)-1),**profile)
 for j,parent in enumerate(rc['parent']):
  if parent<0:continue
  poly=CW.channel_path(points[parent],points[j],profile.get('obstacles',()),profile.get('clearance',0),profile.get('vertical_obstacles',()),return_points=True)
  kind='leaf' if not children[name] and name not in routing.get('nodes',{}) else 'trunk'
  for a,b in zip(poly,poly[1:]):
   if a==b:continue
   layer=('M2' if a[1]==b[1] else 'M3') if kind=='leaf' else ('M4' if a[1]==b[1] else 'M5')
   route_lines.append(dict(driver=name,layer=layer,a=a,b=b))
   # Conservative per-net-edge count; duplicated same-net pieces are not merged.
   lo=[math.floor(min(a[k],b[k])/gcell) for k in [0,1]];hi=[math.floor(max(a[k],b[k])/gcell) for k in [0,1]]
   for x in range(lo[0],hi[0]+1):
    for y in range(lo[1],hi[1]+1):demand[layer,x,y]+=1 if kind=='leaf' else 3
pairs=sl['core_tree']['same_leaf_pairs'];membership={q:l['node'] for l in sl['core_tree']['leaves'] for q in l['sinks']};assert len(pairs)==512 and all(membership[a]==membership[b] for a,b in pairs)
capacity=dict(basis='Clock-only upper-count lower-bound capacity check: unmergedplannedMSTpieces,225nominaltracks per10.8umgcell at48nmpitch,2W/2S consumes3tracks vs1Wleaf1. NO data/PG/abstract/viaaccess reservation; NOTfullcapacitymargin.',clock_only_peak_by_layer={L:max([n for (l,x,y),n in demand.items() if l==L]or[0]) for L in ['M2','M3','M4','M5']},nominal_tracks_per_gcell=225.,data_pg_reserved_capacity='NOT RUN / unavailable',verdict='NOT QUALIFIED: full data+PG+pin-access capacity margin missing')
for file,obj in [('slice.json',sl),('legalization.json',legal),('model_result.json',res),('prediction.json',prediction),('routes.json',route_lines),('capacity.json',capacity),('identity.json',dict(register_sinks=4308,macro_sinks=2,atomic_pairs=512,same_leaf_pairs_pass=True,clock_nodes=len(sl['core_tree']['nodes']),planned_cells=len(plan['cells']),source='intel1:qc-su-lat/vmr_R3 actualposthook4cts.odb; vmr_aligned.txt same4308geometry',qualification='MODEL ONLY; noP&R; source0ps undeclaredparentinput; actualleafroutingrangeM2-M5 withdefaultM2/M3 profiles; clocktrunksM4/M5onlyNDR2W; macroclockM4access explicit'))]:
 (p/file).write_text(json.dumps(obj,indent=1))
print('LEGAL',legal['cells'],legal['max_displacement_um'],'MODEL',res,'CAP',capacity,flush=True)
