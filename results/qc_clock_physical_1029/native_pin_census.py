#!/usr/bin/env python3
"""Report native access failures by authoritative partition/type and bounds."""
import argparse,json,sys,collections,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/die_plan'))
import die_clock_128 as C
import die_infra as DI
p=argparse.ArgumentParser()
for n in ['landing-plan','die-plan','endpoints','failed-prebuild','power','pg','out']:p.add_argument('--'+n,required=True)
a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True);P=DI.load_plan(a.die_plan);l=json.load(open(a.landing_plan));ep=json.load(open(a.endpoints));ep=ep.get('endpoints',ep)
rows=[];bytype=collections.defaultdict(list)
for f in l['failures']:
 inst=f['inst'];part=P.parts.get(inst);r=dict(f)
 if part is None:r['class']='NOT_A_PARTITION_WRAPPER';rows.append(r);continue
 ty=part['type'];bounds=P.rect(inst);x0,y0,x1,y1=f['rect_um'];cy=(y0+y1)/2;h=f['diagnostic_minimum_symmetric_pin_height_um'];max_h=2*min(cy-bounds[1],bounds[3]-cy)
 r.update(type=ty,module=P.types[ty].get('module'),part_bounds_um=list(bounds),part_orient=part.get('orient','R0'),original_layer=ep[f['port']]['original_layer'],maximum_symmetric_height_inside_part_um=round(max_h,6),diagnostic_height_fits_part=(h is not None and h<=max_h+1e-7),classification='GENERIC_SOFT_WRAPPER_CLOCK_PORT' if re.fullmatch(r'clk(?:_t[0-9]+)?',f['pin']) else 'REVIEW_NATIVE_PIN',signed_type_view=P.types[ty].get('view'))
 m=re.fullmatch(r'clk_c([0-9]+)',f['pin'])
 if m:
  core_taps=[q for q in P.types[ty].get('clock',{}).get('taps',[]) if q.get('kind')=='core'];idx=int(m.group(1))
  if idx<len(core_taps):
   tap=core_taps[idx];r['core_tap']=tap['name'];r['core_budget_owner']=tap.get('budget_owner','');r['classification']='SIGNED_CORE_CLOCK_PROXY_PRESERVE' if 'SIGNED' in r['core_budget_owner'] and 'NOT SIGNED' not in r['core_budget_owner'] else 'UNSIGNED_CORE_CLOCK_PROXY_REVIEW'
 if ty.startswith('phy_'):r['classification']='PHY_WRAPPER_CLOCK_REVIEW_PRESERVE'
 rows.append(r);bytype[ty].append(r)
summary=dict(status='DIAGNOSTIC_ONLY_NO_INTERFACE_EDIT',spacing_um=l['spacing_um'],failed=len(rows),types=len(bytype),non_wrapper=sum(r.get('class')=='NOT_A_PARTITION_WRAPPER' for r in rows),classification=dict(collections.Counter(r.get('classification','UNKNOWN') for r in rows)),height_outside_part=sum(not r.get('diagnostic_height_fits_part',False) for r in rows),maximum_diagnostic_height_um=max(r.get('diagnostic_minimum_symmetric_pin_height_um') or 0 for r in rows),per_type={t:dict(pins=len(rr),instances=len({r['inst'] for r in rr}),maximum_required_height_um=max(r['diagnostic_minimum_symmetric_pin_height_um'] or 0 for r in rr),minimum_part_symmetric_height_um=min(r['maximum_symmetric_height_inside_part_um'] for r in rr)) for t,rr in bytype.items()})
json.dump(dict(summary=summary,rows=rows),open(out/'full32_pin_census.json','w'),indent=1);print(summary,flush=True)
# The32 additional failures under the old .08 picker are classified separately.
pg=json.load(open(a.pg));power=json.load(open(a.power));ix=C.MetalIndex(.08)
for s in C.pg_shapes(pg)+C.pg_shapes(power):ix.add(s)
failed=json.load(open(a.failed_prebuild))['findings'];report=[]
for f in failed:
 x=f['reference_xy_um'][0];rr=[]
 for y in f['legal_in_pin_rows_um']:
  hit=ix.hits(('M8',f['port'],'access',y-.04,y+.04,x-.096,x+.096),first=True)
  rr.append(dict(y_um=y,first_blocker=None if not hit else ix.shapes[hit[0][0]],kind=None if not hit else hit[0][1]))
 report.append(dict(port=f['port'],inst=f['inst'],pin=f['pin'],type=P.parts[f['inst']]['type'],rect_um=f['rect_um'],part_bounds_um=list(P.rect(f['inst'])),rows=rr))
json.dump(dict(status='FAIL_RETAINED',spacing_um=.08,pins=len(report),rows=report),open(out/'power32_row_census.json','w'),indent=1);print('POWER_ROWS',len(report),flush=True)
