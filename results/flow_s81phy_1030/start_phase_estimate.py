"""Pre-build unchanged-START feasibility control; shared aperture/phase checker, no physical claim."""
from pathlib import Path
import json,sys
R=Path(__file__).parent;sys.path.insert(0,str(R/'tool_snapshot/tools/die_plan'))
import count_align_plan as C
F=json.load(open(R/'feed_estimate.json'));OLD=json.load(open(R/'old_ocv.json'));SP={'TT':1.0485,'FF':1.0552};out=[]
for a in F['variants']:
 rows=[]
 for e in OLD['start_edges']:
  pn=e['dst'];p=a['parts'][pn]['corners']
  dlo=min(v['endpoint_delta_min']*SP[c] for c,v in p.items());dhi=max(v['endpoint_delta_max']*SP[c] for c,v in p.items())
  r=dict(e,lo=e['lo']+dlo,hi=e['hi']+dhi,fall_lo=e['fall_lo']+dlo,fall_hi=e['fall_hi']+dhi,d_ps=e['d_ps']+(dlo+dhi)/2)
  nv,edge,off,dist,iv=C.sync_choice_iv(r,833,833/8)
  rows.append(dict(part=pn,delta_union_ps=[dlo,dhi],rise_interval_ps=[r['lo'],r['hi']],fall_interval_ps=[r['fall_lo'],r['fall_hi']],best_edge=edge,sync_values=nv,boundary_distance_ps=dist,existing_source_phase_clean=(nv==1)))
 out.append(dict(macro_x_um=a['macro_x_um'],scope='Unchanged old START source; nominal cal-g03 stage deltas across TT/FF with current spice factors. Old variation interval retained as optimistic control; new variation/START routing not yet qualified.',starts=rows,verdict='HELD_REPLAN_START' if any(r['sync_values']>1 for r in rows) else 'MODEL_ONLY',build_allowed=False))
json.dump(dict(variants=out),open(R/'start_phase_estimate.json','w'),indent=1)
for a in out:print(a['macro_x_um'],a['verdict'],[(r['part'],r['best_edge'],r['sync_values'],round(r['boundary_distance_ps'],2),[round(v,2) for v in r['delta_union_ps']]) for r in a['starts']])
