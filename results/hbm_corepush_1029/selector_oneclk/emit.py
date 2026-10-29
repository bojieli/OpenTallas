#!/usr/bin/env python3
"""Emit source-preserving selector pin and clock delta; no physical run/adoption."""
import json,argparse,hashlib,copy
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('plan',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args();a.out.mkdir(exist_ok=False)
r=lambda p:json.loads(p.read_text());w=lambda p,d:p.write_text(json.dumps(d,indent=1)+'\n')
d=r(a.plan/'die_plan.json');ce=r(a.plan/'clock_entries.json');con=r(a.plan/'core_conns.json');events=[]
for ty,t in d['partition_types'].items():
 for h in t.get('hard_cores',[]):
  if h['module']!='ot_hbm_idx_selector_static_sel':continue
  old=r(a.plan/h['pins_file']);removed=[p for p in old if p['name'].startswith(('clk_q[','clk_mem['))];new=[p for p in old if p not in removed];assert len(removed)==16 and len(new)==4767
  assert len([p for p in new if p['name']=='clk_ctl'])==1
  c=copy.deepcopy(ce[ty][h['inst']]);c.update(port='clk_ctl',merged_clock_ports=[],source='CANDIDATE: native wrapper already uses only clk_ctl; remove16unusedtopclockports; freshlocaltree qualification required')
  co=copy.deepcopy(con[ty][h['inst']]);dropped={k:co.pop(k) for k in list(co) if k in ('clk_q','clk_mem') or k.startswith(('clk_q[','clk_mem['))}
  events.append({'type':ty,'inst':h['inst'],'module':h['module'],'origin_um':h['origin_um'],'orient':h.get('orient','R0'),'outline_um':h['outline_um'],'track_offset_um':h.get('track_offset_um',[0,0]),'old_pins_file':h['pins_file'],'old_pins_sha256':hashlib.sha256((a.plan/h['pins_file']).read_bytes()).hexdigest(),'new_pins_file':'selector_oneclk_pins.json','removed_clock_pins':removed,'preserved_pins':len(new),'new_clock_entry':c,'new_core_conns':co,'removed_clock_connections':dropped,'changed_data_control_pins':0,'added_cycles':0})
  w(a.out/'selector_oneclk_pins.json',new)
assert len(events)==1
w(a.out/'plan_event.json',{'status':'UNSIGNED_CANDIDATE; atomiccaller/nativeclockmodel prerequisite','source_plan_sha256':hashlib.sha256((a.plan/'die_plan.json').read_bytes()).hexdigest(),'instances':events})
print('SELECTOR_ONECLK_EVENT',len(events),'instances',len(new),'pins')
