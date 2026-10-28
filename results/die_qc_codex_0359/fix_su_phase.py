import json,sys,shutil
from pathlib import Path
src,out=map(Path,sys.argv[1:3]);p=json.load(open(src)); signed=src.parent/'cores/su/signed'; changed=[]
for tn,t in p['partition_types'].items():
 taps={r['name']:r for r in t.get('clock',{}).get('taps',[])}
 for h in t.get('hard_cores',[]):
  f=signed/(h['module']+'_pins.json')
  if not f.exists():continue
  assert h.get('orient','R0')=='R0',h
  assert h.get('track_offset_um')==[0.,0.],h
  pins=json.load(open(f))
  for pin in pins:
   coord=pin['y'] if int(pin['layer'][1:])%2==0 else pin['x']
   assert abs((coord*1000)%48-12)<1e-5,(h['module'],pin)
  assert all(abs(v*1000%48)<1e-5 or abs(v*1000%48-48)<1e-5 for v in h['origin_um']),h
  h['track_offset_um']=[.012,.012]
  tap=taps[h['inst']+'.ck'];tap['xy']=[round(v+.012,3) for v in tap['xy']]
  changed.append(dict(type=tn,inst=h['inst'],module=h['module'],offset_um=[.012,.012]))
assert len(changed)==21,len(changed)
shutil.copytree(src.parent,out,ignore=shutil.ignore_patterns('g0c','g0c.log'),dirs_exist_ok=False,symlinks=True)
(out/'qc_k2b_phase12.json').write_text(json.dumps(p,indent=1)+'\n')
(out/'su_phase_delta.json').write_text(json.dumps(dict(scope='Signed native pins unchanged; grid offset only; zero cycle/FF delta',changes=changed),indent=2)+'\n')
print('signed core placements corrected',len(changed))
