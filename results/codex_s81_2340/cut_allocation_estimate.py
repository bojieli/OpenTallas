#!/usr/bin/env python3
"""Estimate explicit FT channel share needed at the unchanged0.6 cut limit; never edits canonical plan."""
import json,sys,copy
sys.path.insert(0,'tools/die_plan')
import schema as S,check as C
raw=json.load(open(sys.argv[1]));P=S.Plan(raw);geo={lid:C.lane_geometry(P,lid) for lid in P.lanes}
changes={};runs=[]
for k in range(4):
 P=S.Plan(raw);R=C.Report();out=C.check_cuts(P,R,geo);err=R.errors();runs.append(dict(round=k,errors=err,worst=out['worst_partition_segment']))
 print('ROUND',k,len(err),out['worst_partition_segment'],flush=True)
 if not err:break
 changed=False
 for e in err:
  part=e.get('part')
  if not part:continue
  tn=P.parts[part]['type'];old=raw['partition_types'][tn].get('ft_track_frac',C.FT_TRACK_FRAC)
  if old<.5:
   changes[tn]=dict(old=old,new=.5,parts=[n for n,p in P.parts.items() if p['type']==tn]);raw['partition_types'][tn]['ft_track_frac']=.5;changed=True
 if not changed:break
json.dump(dict(label='ESTIMATEONLY_NOTPHYSICALLYRESERVED',cut_limit=raw['budgets']['cut_ratio_max'],proposed_share=.5,changes=changes,runs=runs,limitations=['FT share changes must become actual per-layer reserved tracks/bands and prove remaining local/core-link routing demand before adoption.','No source/pin/core/interface/latency change in this estimate.','No GRT/STA or canonical plan adoption.']),open(sys.argv[2],'w'),indent=2)
