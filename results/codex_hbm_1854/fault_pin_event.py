#!/usr/bin/env python3
"""Fix HBM sfustore observation fault-pin reach; pure geometry, zero data cycles."""
import json,sys,os,hashlib
from pathlib import Path
src,out=map(Path,sys.argv[1:3]);out.mkdir(parents=True,exist_ok=False)
r=json.loads((src/'die_plan.json').read_text());changed=[];tables={}
for tn,t in r['partition_types'].items():
 for h in t.get('hard_cores',[]):
  if h.get('module')!='ot_hbm_su_static_sfustore_hw':continue
  old=h['pins_file'];new=old.removesuffix('.json')+'_fault_s18.json'
  if old not in tables:
   pins=json.loads((src/old).read_text());q=[p for p in pins if p['name']=='fault'];assert len(q)==1
   assert q[0]['layer']=='M4' and abs(q[0]['x']-362.784)<.001
   before=dict(q[0]);q[0].update(layer='M5',x=8.64,y=.096)
   assert all(p is q[0] or p.get('layer')!='M5' or abs(p['x']-8.64)>=.144 or abs(p['y']-.096)>=.144 for p in pins)
   tables[old]=(new,pins,before)
  h['pins_file']=new;changed.append([tn,h['inst'],old,new])
assert len(changed)==4
for f in src.iterdir():
 if f.name in ('die_plan.json','cores'):continue
 os.symlink(f.resolve(),out/f.name)
(out/'cores').mkdir()
for f in (src/'cores').iterdir():os.symlink(f.resolve(),out/'cores'/f.name)
for old,(new,pins,before) in tables.items():
 (out/new).write_text(json.dumps(pins,indent=1)+'\n')
(out/'die_plan.json').write_text(json.dumps(r,indent=1)+'\n')
report=dict(change='fault observation pin E to S, no RTL or cycle change',instances=changed,oldpins={k:v[2]for k,v in tables.items()},newpin=dict(layer='M5',x=8.64,y=.096),old_reach_um=559.76,new_estimated_flop_to_pin_um=45.7,estimate_only=True,plan_sha=hashlib.sha256((out/'die_plan.json').read_bytes()).hexdigest())
(out/'fault_pin_report.json').write_text(json.dumps(report,indent=1)+'\n');print(report)
