from pathlib import Path
import json,hashlib,shutil,sys
r=Path('/srv/opentallas-scratch2/claude/codex-q6-resume-prep-0230');sys.path.insert(0,str(r/'flow_source/tools/autopilot'));import kit_resume as K
old=Path('/srv/opentallas-scratch2/claude/codex-kv-ahub-1131/kits/recip_native216');s=r/'source/recip';c=r/'candidate/recip';base=Path('run/results/asap7/hc_ot_qkh_recip_leaf__216x216/base');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n in K.STEP_OUT['synth']:assert sha(old/base/n)==sha(s/base/n)
f=old/'adder_map_dontuse.v';assert f.stat().st_mtime < (old/base/'1_2_yosys.v').stat().st_mtime
lg=old/'run/logs/asap7/hc_ot_qkh_recip_leaf__216x216/base/1_2_yosys.log';assert 'Verilog-2005 frontend: /work/adder_map_dontuse.v' in lg.read_text()
report=json.loads((old/'adder_map_dontuse.json').read_text());assert report['verdict']=='PASS'
for name,k in [('source',s),('candidate',c)]:
 assert not (k/f.name).exists();shutil.copy2(f,k/f.name)
 shutil.copy2(k/K.INPUTS_FILE,r/('recip_inputs_before_map_'+name+'.json'));(k/K.INPUTS_FILE).unlink();K.write_inputs(str(k))
rec={'native_source':str(old),'map_sha256':sha(f),'original_map_mtime':f.stat().st_mtime,'mapped_checkpoint_mtime':(old/base/'1_2_yosys.v').stat().st_mtime,'three_synth_outputs_exact':True,'log_records_map_read':True,'source_and_candidate_map_exact':sha(s/f.name)==sha(c/f.name)==sha(f),'changed_rtl_sdc_or_synth_outputs':False,'normal_input_records_recaptured':True,'old_records_preserved':True}
(r/'RECIP_AUTHENTIC_ADDER_MAP_JOIN.json').write_text(json.dumps(rec,indent=2)+'\n');shutil.copy2(old/'adder_map_dontuse.json',r/'RECIP_AUTHENTIC_ADDER_MAP_REPORT.json')
om=K.manifest(str(s),runner=str(s/'run_kit_kv.sh'));nm=K.manifest(str(c),runner=str(c/'run_kit_kv.sh'));d=K.decide(nm,om)
for n,a in [('recip_source_manifest_mapjoin',om),('recip_candidate_manifest_mapjoin',nm),('recip_decision_mapjoin',d)]: (r/(n+'.json')).write_text(json.dumps(a,indent=2)+'\n')
print(json.dumps(rec,indent=2));print(json.dumps(d,indent=2))
