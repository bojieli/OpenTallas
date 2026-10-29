#!/usr/bin/env python3
"""One source-only S81 PHY/FT/landing relayout event. All original failed plans remain."""
import copy,importlib.util,json,sys
from pathlib import Path
sys.path.insert(0,'tools/die_plan')
import clock_landing_plan as CL
s=importlib.util.spec_from_file_location('s12','results/die_s81_19_1028/scripts/recompose_s12.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
b=Path(sys.argv[1]);raw=json.load(open(b/'ft_reserve/plan_ft_allocated.json'));patches=[]
for f in sorted((b/'landing_shift3').glob('*.candidate.json')):patches.append(json.load(open(f)))
patches.append(json.load(open(b/'landing_native_order/svc_hi_dsdv_svc_rs__t3.candidate.json')))
patches.append(json.load(open(b/'landing_bank_relief/svc_hi_dsdv_svc_rs__t5.candidate.json')))
orders={};seen=set()
for p in patches:
 tn=p['type'];assert tn not in seen;seen.add(tn);t=raw['partition_types'][tn];dx,dy=p['translation_um']
 for c in t.get('hard_cores',[]):c['origin_um']=[round(c['origin_um'][0]+dx,6),round(c['origin_um'][1]+dy,6)]
 for f in t.get('ft_slots',[]):
  if f.get('regs_um'):f['regs_um']=[f['regs_um'][0]]+[[round(x+dx,6),round(y+dy,6)]for x,y in f['regs_um'][1:]]
  if f.get('bit_sites_um'):f['bit_sites_um']=[[[round(x+dx,6),round(y+dy,6)]for x,y in st]for st in f['bit_sites_um']]
 for e in p.get('bank_relief',[]):
  f=next(f for f in t['ft_slots']if f['name']==e['slot']);j=e['internal_stage'];ex,ey=e['delta_um']
  f['bit_sites_um'][j-1]=[[round(x+ex,6),round(y+ey,6)]for x,y in f['bit_sites_um'][j-1]]
  f['regs_um'][j]=[round(f['regs_um'][j][0]+ex,6),round(f['regs_um'][j][1]+ey,6)]
 for c in t.get('clock',{}).get('taps',[]):
  if c.get('kind')=='core':c['xy']=[round(c['xy'][0]+dx,6),round(c['xy'][1]+dy,6)]
 for r in t.get('internal_stations',[]):
  for k in ('from_um','to_um'):r[k]=[round(r[k][0]+dx,6),round(r[k][1]+dy,6)]
  r['regs_um']=[[round(x+dx,6),round(y+dy,6)]for x,y in r['regs_um']]
 if p.get('band_order')=='largest_first':orders[tn]='largest_first'
 t['note']=t.get('note','')+f'; SOURCE CANDIDATE ONLY: same-outline landing bay relayout, macro/internal FT translation {dx},{dy}um; no RTL/pin/data-cycle change. Clock/reset/PG and partner reach require fresh composition.'
raw['note']=raw.get('note','')+'; CODEX S81 one source event: ES shoreline V2 + actual FT complement + landing bay relayout; SOURCE CANDIDATE NOT ADOPTED'
out=b/(sys.argv[2] if len(sys.argv)>2 else 'batch02');out.mkdir(exist_ok=True)
for name in ('inputs','census','census_map.json','cells_est.json','core_conns.json'):
 target=out/name
 if not target.exists():target.symlink_to(Path('..')/name)
if not (out/'physical').exists():(out/'physical').symlink_to('../../main_src/physical')
src=out/'plan_source.json';src.write_text(json.dumps(raw,indent=1))
(out/'event.json').write_text(json.dumps(dict(scope='SOURCE_CANDIDATE_ONLY',patches=patches,band_order_by_type=orders,added_payload_flops=3586,added_cycles={'coll__s_7S_LP__lk_ES1':6,'coll__lk_ES1__s_7S_LP':1}),indent=1))
print('BATCH_SOURCE',len(patches),'types',orders,flush=True)
new,sc=CL.compose(raw,json.load(open(b/'landed_crossings_r98.json')),plan_path=str(src),observer_part=m.OBS_PART,observer=dict(m.OBS),band_order_by_type=orders)
(out/'plan_composed.json').write_text(json.dumps(new,indent=1));(out/'sidecar.json').write_text(json.dumps(sc,indent=1))
print('COMPOSE',json.dumps(dict(placement_failures=sc['collector']['placement_failures'],max_die_hop_um=sc['collector']['max_die_hop_um'],boot_ready=sc['collector']['boot_budget']['ready_at_glue_max_cycles'])),flush=True)
