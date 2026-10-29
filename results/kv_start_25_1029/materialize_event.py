#!/usr/bin/env python3
import hashlib,json,shutil,sys,os
from pathlib import Path
R=Path(sys.argv[1]);W=Path(sys.argv[2]);src=R/'event26';out=W/'results/kv_start_25_1029/event26';out.mkdir(parents=True,exist_ok=True);co=out.parent/'cores';co.mkdir(exist_ok=True)
p=json.load(open(src/'plan_native_pins.json'));count=0
for t in p['partition_types'].values():
 for h in t.get('hard_cores',[]):
  if not h.get('pins_file'):continue
  f=Path(h['pins_file']);f=f if f.is_absolute() else src/f
  b=f.read_bytes();name=f.stem+'_'+hashlib.sha256(b).hexdigest()[:12]+f.suffix
  (co/name).write_bytes(b);h['pins_file']='../cores/'+name;count+=1
for c in p.get('census',[]):
 for key in ('rows','map','bitcon'):
  if not c.get(key):continue
  f=Path(c[key]);f=f if f.is_absolute() else src/f
  if not f.exists():f=W/'physical/die_plan/qwen_kvsys'/c[key]
  assert f.is_file(),f
  # Keep referenced census records in the owned source rather than an external predecessor.
  b=f.read_bytes();name=f.stem+'_'+hashlib.sha256(b).hexdigest()[:12]+f.suffix;(co/name).write_bytes(b);c[key]='../cores/'+name
(out/'plan.json').write_text(json.dumps(p,indent=1))
for name in ('sidecar.json','regions_ca.json','straps.json','summary.json','boundary_map.json'):
 shutil.copyfile(src/name,out/name)
shutil.copytree(src/'latency',out/'latency',dirs_exist_ok=True)
recipe=Path('physical/die_plan/qwen_kvsys/dcal_rom/bind/position2144b19/recipe_kv24_t2.json');d=json.load(open(W/recipe));d['clock_landing_table']='results/kv_start_25_1029/event26/sidecar.json'
# Keep qualified data padding until its signature is regenerated against this new source event.
newrecipe=W/recipe.parent/'recipe_kv26.json';newrecipe.write_text(json.dumps(d,indent=1))
print(json.dumps(dict(core_slots=count,plan=str(out/'plan.json'),recipe=str(newrecipe))))
