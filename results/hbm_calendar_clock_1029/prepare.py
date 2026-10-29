"""Build private ONECLK+WCFG calendar trial inputs from accepted compact frame."""
import hashlib,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
base=root/'results/hbm_calendar_1029'
pdir=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=False)
def dump(path,data):path.write_text(json.dumps(data,indent=1)+'\n')
old='hfd_hgi_vm_calendar_f20';new=old+'_oneclk'
pins=json.loads((base/'cfg_w/pins.json').read_text())
assert len(pins)==558
pins=[p for p in pins if p['name'] not in ['clk_cap','clk_mem','clk_tgt']]
assert len(pins)==555
pinpath=pdir/'cores'/f'{new}__216x112.32__cfg_w.json';dump(pinpath,pins)
sha=hashlib.sha256(pinpath.read_bytes()).hexdigest();plan=json.loads((pdir/'die_plan.json').read_text());hit=[]
for tn,t in plan['partition_types'].items():
 for c in t.get('hard_cores',[]):
  if c['module']!=old:continue
  assert c['outline_um']==[216.,112.32]
  c['module']=new;c['pins_file']='cores/'+pinpath.name
  for k in ['lef','lib']:c.pop(k,None)
  c['status']='PENDING-VIEW';hit.append([tn,c['inst']])
 for c in t.get('contents',[]):
  if c.get('module')==old:c['module']=new
assert len(hit)==4,hit
dump(pdir/'die_plan.json',plan)
v=json.loads((pdir/'views.json').read_text());assert len(v['view_list'])==1
v['plan']='die_plan.json';q=v['view_list'][0];q.update(module=new,view=new+'@'+sha[:12],pins_file='cores/'+pinpath.name,pins_sha256=sha,pins=555)
dump(pdir/'views.json',v)
sl=json.loads((base/'master_slice.json').read_text());sl.update(type=new,module=new)
dump(out/(new+'.json'),sl)
dump(out/'trial_inputs.json',dict(status='GEN_PLACE_ONLY_RESET_GRAFT_OPEN',module=new,view=q['view'],pins=555,changes=hit,cycles_added=0,source_proof='codex/hbm-calendar-0320@0f0c51e62',recipe_key=old,macro_instance='u_calendar.u_programme.u_program',guide=json.loads((base/'cfg_w/data_guide.json').read_text())))
print(q['view'])
