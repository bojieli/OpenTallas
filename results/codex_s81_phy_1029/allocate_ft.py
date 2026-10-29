#!/usr/bin/env python3
"""Source-only S81 channel allocation with physical complementary track maps."""
import json,sys
from pathlib import Path
sys.path.insert(0,'tools/die_plan')
import schema as S,check as C,partition_ft_reserve as FT
raw=json.load(open(sys.argv[1]));out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
changes={};runs=[]
for iteration in range(4):
 P=S.Plan(raw);r=C.Report();geo={n:C.lane_geometry(P,n) for n in P.lanes};res=C.check_cuts(P,r,geo)
 print('CUT_ROUND',iteration,len(r.errors()),res['worst_partition_segment'],flush=True)
 runs.append(dict(iteration=iteration,errors=r.errors(),worst=res['worst_partition_segment']))
 if not r.errors():break
 touched=False
 for e in r.errors():
  part=e.get('part')
  if not part:continue
  tn=P.parts[part]['type'];t=raw['partition_types'][tn];w,h=t['outline_um']
  if t.get('die_ft_bands'):continue
  t['ft_track_frac']=.5
  t['die_ft_bands']=[dict(dir='EW',span_um=[0,h],layers=['M4','M5','M6','M7'],die_share=.5)]
  changes[tn]=dict(instances=[n for n,p in P.parts.items() if p['type']==tn],bands=t['die_ft_bands'],ft_track_frac=.5)
  touched=True
 if not touched:break
P=S.Plan(raw);json.dump(raw,open(out/'plan_ft_allocated.json','w'),indent=1)
json.dump(dict(scope='SOURCE_CANDIDATE_NOT_PHYSICAL_QUALIFICATION',cut_limit=raw['budgets']['cut_ratio_max'],changes=changes,runs=runs),open(out/'cut_changes.json','w'),indent=2)
for tn,t in sorted(P.types.items()):
 if not t.get('die_ft_bands'):continue
 try:
  receipt=FT.reservation(P,tn)
  json.dump(receipt,open(out/(tn+'.reservation.json'),'w'),indent=1)
  (out/(tn+'.reservation.tcl')).write_text(FT.tcl(receipt))
  print('RESERVED',tn,len(receipt['rectangles_um']),receipt['instances'],flush=True)
 except Exception as e:
  print('RESERVATION_FAIL',tn,type(e).__name__,str(e),flush=True)
