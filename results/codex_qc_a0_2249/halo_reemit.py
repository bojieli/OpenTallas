"""Re-emit the already-compiled A0 plan after coordinate-only macro-branch halo correction.
No clock identity, topology, stage, load, contract or flow guard changes.
"""
import json,sys,copy
from pathlib import Path
sys.path.insert(0,str(Path('tool_snapshot/tools/die_plan').resolve()))
import core_infra as CI
kd,new=Path(sys.argv[1]),json.load(open(sys.argv[2]));old=json.load(open(kd/'master_slice.json'))
changed={}
for a,b in zip(old['core_tree']['nodes'],new['core_tree']['nodes']):
 assert a['name']==b['name']
 aa,bb=copy.deepcopy(a),copy.deepcopy(b);xa,xb=aa.pop('xy_um'),bb.pop('xy_um');assert aa==bb
 if xa!=xb:
  assert a['name'].startswith('mp_p2p_macro_')
  assert abs(xa[0]-xb[0])+abs(xa[1]-xb[1])<5
  changed[a['name']]=xb
assert old['core_tree']['leaves']==new['core_tree']['leaves']
assert old['core_tree']['gates']==new['core_tree']['gates']
compiled=json.load(open(kd/'core_infra_plan.json'))
for c in compiled['cells']:
 if c['name'] in changed:c['xy_um']=changed[c['name']]
for n in compiled['core_tree']['nodes']:
 if n['name'] in changed:n['xy_um']=changed[n['name']]
text=CI.emit_late_tcl(compiled)
for f in ('core_infra_plan.json','master_core_infra_late.tcl','master_slice.json'):
 src=kd/f;dst=kd/(f+'.before_halo_r1')
 if not dst.exists():dst.write_bytes(src.read_bytes())
for f,data in [('core_infra_plan.json',json.dumps(compiled,indent=1)+'\n'),('master_core_infra_late.tcl',text),('master_slice.json',json.dumps(new,indent=1)+'\n')]:
 temp=kd/(f+'.tmp');temp.write_text(data);temp.replace(kd/f)
(kd/'PREP_AD2PR1_OK.json').write_text(json.dumps(dict(coordinate_only=True,corrected_nodes=len(changed))))
print('PREP_AD2PR1_OK',len(changed))
