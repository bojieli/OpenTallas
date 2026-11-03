"""One normal collector pass on exactly the completed HEAD94510 records; no tick/launch/cancel."""
import json,sys,fcntl,copy
from pathlib import Path
sys.path.insert(0,str(Path('/home/ubuntu/OpenTallas/tools/autopilot').resolve()))
import kit_wave as K,autopilot as AP
apply='--apply' in sys.argv;AP.DRY=not apply
lk=open(K.AP_DIR/'kit_wave.lock','w');fcntl.flock(lk,fcntl.LOCK_EX|fcntl.LOCK_NB)
assert K.scheduler_current(AP),'scheduler source changed; defer without bypass'
cfg=K.load_config(AP.read_coord('autopilot/kit_wave.json'));full=K.load_state();picked={k:v for k,v in full['items'].items() if v.get('die')=='s81_head' and str(v.get('unit','')).endswith('-94510') and v.get('status')=='RUNNING'}
assert len(picked)<=4
for k,v in picked.items():
 assert not AP.unit_active(v['unit']),('still active',k)
 r=json.loads((Path(v['dir'])/'result.json').read_text());assert r.get('stage')=='geom',k
 assert v['item'] in ('hd_spn_eshim_tx','hd_st_n3_transit','hd_st_n3_turn','hd_mesh_e')
sub=copy.deepcopy(full);sub['items']=copy.deepcopy(picked);notices={};K.collect(AP,cfg,sub,notices)
print(json.dumps({'apply':apply,'records':{k:{x:v.get(x) for x in ('status','stage','class','reason','geom_verdict','kit')} for k,v in sub['items'].items()},'notices':notices},indent=1))
if apply:
 full['items'].update(sub['items']);full['pass_n']=sub.get('pass_n',full.get('pass_n',0));K.save_state(full);K.write_stages(full,K.AP_DIR,cfg)
