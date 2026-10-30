#!/usr/bin/env python3
"""PREBUILD mixed-cell geometry with explicit proposed soft-partition islands.
Preserve all actual higher-layer/hard OBS. Only recompute soft M1-M3 opacity
with the existing island constructor; native M7 PG uses its existing cut rule.
No ODB or source LEF is modified. Final actual-source readback remains required.
"""
import argparse,collections,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--actual-geometry',required=True);p.add_argument('--die-plan',required=True);p.add_argument('--old-clock-windows',required=True);p.add_argument('--provider-windows',required=True);p.add_argument('--provider-pins',required=True);p.add_argument('--tools',required=True);p.add_argument('--out',required=True);a=p.parse_args();sys.path.insert(0,a.tools);import schema,die_trial,landing_route
P=schema.Plan(schema.load(a.die_plan),Path(a.die_plan));g=json.load(open(a.actual_geometry));old=json.load(open(a.old_clock_windows));new=json.load(open(a.provider_windows));pins=json.load(open(a.provider_pins));D=g['dbu'];assert not new['blocked'] and not new['outside'];assert pins['actual_ODB_bound'] is False
combined={t:sorted(set(map(tuple,old.get('windows',{}).get(t,[])))|set(map(tuple,new.get('windows',{}).get(t,[])))) for t in P.types};free={t:die_trial.rect_minus(*P.types[t]['outline_um'],combined[t]) for t in P.types};ob=[];hard_kept=0
for owner,ly,*r in g['obstructions']:
 if owner in P.parts and ly in ['M1','M2','M3']:continue
 ob.append([owner,ly,*r]);hard_kept+=ly not in ['M1','M2','M3']
def die_rect(part,r):
 aa=P.to_die(part,r[:2]);bb=P.to_die(part,r[2:]);return [round(min(aa[0],bb[0])*D),round(min(aa[1],bb[1])*D),round(max(aa[0],bb[0])*D),round(max(aa[1],bb[1])*D)]
for part,q in P.parts.items():
 t=q['type']
 for ly in ['M1','M2','M3']:
  for r in free[t]:ob.append([part,ly,*die_rect(part,r)])
# Validate that no proposed type-union window carves a hard core, including in
# empty mirrored instances. Old actual higher-layer/hard OBS are kept verbatim.
for t,ww in combined.items():
 for r in ww:
  for x0,y0,x1,y1,*rest in die_trial.core_obs(P.types[t]):
   if x0<r[2] and r[0]<x1 and y0<r[3] and r[1]<y1:raise ValueError('island intersects a declared hard core '+t)
# Current scalar ABI is declared by the parent plan. Replace the old nearest-
# GLUE START pins with that exact native ABI, without relabelling it actual ODB.
scalar={}
for part,q in P.parts.items():
 for pp in landing_route.scalar_pins(P,q['type']):
  x,y=pp['xy_um'];scalar[part,pp['name']]=[part,pp['name'],pp['layer'],*die_rect(part,[x-.04,y-.216,x+.04,y+.216])]
sig=[r for r in g['signal_shapes'] if (r[0],r[1]) not in scalar];sig.extend(scalar.values());sig.extend(pins['signal_shapes'])
supply=[r for r in g['existing_supplies'] if r[1]!='M7'];pgtype={}
for t in P.types:
 w,h=P.types[t]['outline_um'];out=[]
 for net,j in [('VDD',0),('VSS',1)]:
  xx=4.128+j*.384
  while xx+.144<w:
   for r in die_trial._cut_vertical((xx-.144,0,xx+.144,h),combined[t]):out.append((net,'M7',r))
   xx+=8.64
 pgtype[t]=out
for part,q in P.parts.items():
 for n,ly,r in pgtype[q['type']]:supply.append([n,ly,*die_rect(part,r)])
g['cells'].extend(dict(inst=q['inst'],master=q['master'],orient=q['orient'],bbox_dbu=q['bbox_dbu']) for q in pins['instances']);g['obstructions']=ob;g['signal_shapes']=sig;g['existing_supplies']=supply;g['source_kind']='PROJECTED_PREBUILD_EXPLICIT_ISLANDS_NOT_ACTUAL_ODB';g['actual_ODB_bound']=False;g['projection_inputs']=vars(a);out=Path(a.out);out.mkdir(parents=True,exist_ok=True);json.dump(g,open(out/'geometry.json','w'),separators=(',',':'));json.dump(dict(schema='ot_island_windows/1',proposal_only=True,windows=combined),open(out/'combined_islands.json','w'),separators=(',',':'))
result=dict(cells=len(g['cells']),new_provider_cells=len(pins['instances']),signal_rectangles=len(sig),obstructions=len(ob),preserved_higher_or_block_OBS=hard_kept,native_macro_supply_rectangles=len(supply),type_union_island_windows=sum(map(len,combined.values())),actual_ODB_bound=False,scope='Projected mixed-cell PREBUILD. Every actual higher-layer/hard obstruction preserved; fresh actual source readback required')
(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
