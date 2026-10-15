#!/usr/bin/env python3
"""Reconcile assigned real-PC prototype homes against incomplete candidate boxes."""
import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'results/arch/hbm_system_geometry_1015'
a=json.loads((p/'physical_assignments/native_PC_340cfd747.json').read_text())
w,h=a['outline_um'];results={}
for filename in ['forward_D_geometry.json','compact_shared_alternative.json','head_cohort_alternative.json']:
 d=json.loads((p/filename).read_text());hits=[]
 for quarter,frame in a['system_candidate_homes'].items():
  for i,(x,y) in enumerate(frame['pc_origins_um']):
   for name,b in d['boxes'].items():
    if min(x+w,b['x']+b['w'])>max(x,b['x'])+1e-6 and min(y+h,b['y']+b['h'])>max(y,b['y'])+1e-6:
     hits.append({'pc':f'{quarter}_{i}','box':name})
 results[filename]={'pc_rectangle_overlap_count':len(hits),'overlaps':hits}
record={'status':'RECTANGLE_ONLY_UNQUALIFIED','sources':'native_PC_340cfd747.json exact128origins vs current source-derived/provisional candidates','results':results}
(p/'physical_assignments/native_PC_candidate_overlap_audit.json').write_text(json.dumps(record,indent=2)+'\n')
print({k:v['pc_rectangle_overlap_count']for k,v in results.items()})
