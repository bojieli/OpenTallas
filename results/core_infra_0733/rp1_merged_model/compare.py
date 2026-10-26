import json
from pathlib import Path
import core_infra_plan as CP
from core_infra_search import Model
p=Path('.');data=json.load(open('input.json'));s=json.load(open('slice.json'));routing=json.load(open('actual_leaf_layer_prototype.json'))['routing_model']
for branch in [routing['leaf'],routing['nonleaf'],*routing['nodes'].values()]:branch['merge_collinear']=True
m=Model(s,data['libraries'],data['points'],data['caps'],0,0,input_slew_ps=0,routing_model=routing);res=m.evaluate([n['master'] for n in s['core_tree']['nodes']]);prediction=CP.predict_tree(s,data['libraries'],data['points'],data['caps'],0,0,input_slew_ps=0,routing_model=routing)
report=dict(result=res,routing_model=routing,wire_geometry=m.wire_summary,qualification='MODEL-ONLY conditional; merged same-layer conductor union, onlydeclaredturn/pinvias, loops solved; zeroR/Cvias/no coupling orfullcapacitymargin; no empiricalcorrection ordriverchange')
(p/'merged_report.json').write_text(json.dumps(report,indent=1));(p/'merged_prediction.json').write_text(json.dumps(prediction,indent=1));print(res,flush=True);print('wire',sum(r.get('original_tree_wire_um',r['wire_um']) for r in m.wire_summary),sum(r['wire_um'] for r in m.wire_summary),'removed',sum(r.get('overlap_removed_um',0) for r in m.wire_summary),'peak_fraction',max(r.get('overlap_removed_fraction',0) for r in m.wire_summary))
