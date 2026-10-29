#!/usr/bin/env python3
"""Native two-writer qcore pin cut, retaining exact live writer2/3 physical homes.
Only q1 has selected-source producers. No routes or source adoption are performed.
"""
import argparse,json,re,hashlib
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('plan',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args();a.out.mkdir(exist_ok=False)
r=lambda p:json.loads(p.read_text());w=lambda p,d:p.write_text(json.dumps(d,indent=1)+'\n');d=r(a.plan/'die_plan.json');events=[];mapping=[];removed=[];outpins=None
for ty,t in d['partition_types'].items():
 for h in t.get('hard_cores',[]):
  if h['module']!='ot_hbm_su_static_qcore_r13' or not h['inst'].endswith('__q1'):continue
  old=r(a.plan/h['pins_file']);new=[];maps=[];dead=[]
  for p in old:
   q=dict(p);m=re.fullmatch(r'(rf_wv|rf_wa|rf_wd)\[(\d+)\]',q['name'])
   if m:
    base,bit=m[1],int(m[2]);offset={'rf_wv':2,'rf_wa':16,'rf_wd':64}[base]
    if bit<offset:dead.append(p);continue
    q['name']=f'{base}[{bit-offset}]';maps.append({'native_outer_pin':q['name'],'old_inner_physical_pin':p['name'],'pin_um':[p['x'],p['y']]})
   new.append(q)
  assert len(dead)==82 and len(maps)==82 and len(new)==len(old)-82
  assert len({p['name']for p in new})==len(new)
  if outpins is not None:assert outpins==new
  else:outpins=new;mapping=maps;removed=dead
  events.append({'type':ty,'inst':h['inst'],'old_module':h['module'],'new_module':'ot_hbm_su_static_qcore_r13_w2','origin_um':h['origin_um'],'orient':h.get('orient','R0'),'track_offset_um':h.get('track_offset_um',[0,0]),'outline_um':h['outline_um'],'old_pins_file':h['pins_file'],'old_pins_sha256':hashlib.sha256((a.plan/h['pins_file']).read_bytes()).hexdigest(),'pins_before':len(old),'pins_after':len(new),'clock_reset_geometry_unchanged':True,'native_mapping':{'MUTW':0,'inner_writer_offset':2},'source_cycles_added':0})
assert len(events)==2
w(a.out/'pins_w2.json',outpins);w(a.out/'plan_event.json',{'status':'UNSIGNED_CANDIDATE noGEN untilsourceclock/tap eventcoherent','source_plan_sha256':hashlib.sha256((a.plan/'die_plan.json').read_bytes()).hexdigest(),'instances':events,'live_writer_bit_mapping':mapping,'removed_dead_inner_writer_pins':removed,'q0_status':'UNREALIZED selectedsource; untouchedbythiscandidate','clock_dependency':'CurrentCEroot151.176112.32 vsoldphysical112.86 andstalesplit73.464tap mustbe fixed atomically, nottrimmed','transport_dependency':'Use native_w2 portbits aftermodule/pin event; genericouter0→oldinner0 forbidden'})
print('QCORE_W2_EVENT',len(events),'instances',len(outpins),'pins')
