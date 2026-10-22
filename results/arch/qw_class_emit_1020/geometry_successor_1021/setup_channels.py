from pathlib import Path
import importlib.util,json,hashlib,shutil
s=Path('/srv/opentallas-scratch/claude/codex-qw-classgeom0105')
old='/srv/opentallas-scratch/claude/codex-qw-classgeom0030'
helper=Path('/srv/opentallas-scratch/claude/classgeom_receiver_plan.py')
spec=importlib.util.spec_from_file_location('channel',helper);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
plan=m.expand_channel(json.loads((s/'receiver_plan.json').read_text()),'dvs_E2',129.6,32983.176,24288.824,west=129.6)
plan['receiver_channel_plan']['western_service_clearance_consumed_um']=129.6
plan['receiver_channel_plan']['core_feed_bump_xy_um']=[17409.6,12096.0]
plan['receiver_channel_plan']['core_feed_bump_moved']=False
(s/'receiver_plan.json').write_text(json.dumps(plan,indent=1)+'\n')
shutil.copy2(helper,s/'src/tools/qwen_split/dv_receiver_channel_plan.py')
for name in ['gen.sh','run.sh','run_candidate.sh']:
 p=s/name;p.write_text(p.read_text().replace(old,str(s)))
for name in ['out','out.log','GEN_DONE','FINAL_GEN_FAIL','landplan_check.txt','land_plan_used.json','gen_safety_facts.json']:
 p=s/name
 if p.is_dir():shutil.rmtree(p)
 elif p.exists():p.unlink()
d=json.loads((s/'source.json').read_text());d['source_commit']='3403b5c23';d['predecessor']=old;d['predecessor_terminal']='FAIL class rly_dv_ch_E1_ar_ard_0 blocked dvs_E2; preserved immutable';d['recipe']='B channel plus explicit E1/E2 expansion and west array translation';d['geometry_plan']=plan['receiver_channel_plan'];d['sha256']={f:hashlib.sha256((s/f).read_bytes()).hexdigest() for f in d['sha256']};d['sha256']['src/tools/qwen_split/dv_receiver_channel_plan.py']=hashlib.sha256(helper.read_bytes()).hexdigest();(s/'source.json').write_text(json.dumps(d,indent=2)+'\n')
