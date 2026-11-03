from pathlib import Path
import json,hashlib,shutil,sys
r=Path('/srv/opentallas-scratch2/claude/codex-q6-resume-prep-0230');sys.path.insert(0,str(r/'flow_source/tools/autopilot'));import kit_resume as K
s=r/'source/recip';c=r/'candidate/recip';old=Path('/srv/opentallas-scratch2/claude/codex-kv-ahub-1131/kits/recip_native216');base=Path('run/results/asap7/hc_ot_qkh_recip_leaf__216x216/base');logs=Path(str(base).replace('/results/','/logs/'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();proof={n:{'source_copy':sha(s/base/n),'native_original':sha(old/base/n)} for n in K.STEP_OUT['synth']};assert all(v['source_copy']==v['native_original'] for v in proof.values())
joined={}
for n in K.STEP_LOGS['synth']:
 assert not (s/logs/n).exists();assert not K.ERR_LINE.search((old/logs/n).read_text(errors='replace'));shutil.copy2(old/logs/n,s/logs/n);joined[n]=sha(s/logs/n)
rec=dict(native_original=str(old),original_compact_source='/srv/opentallas-scratch2/claude/codex-pickup-kv/recip_c138_place1',three_checkpoints_exact=proof,authentic_log_sha256=joined,own_copy_only=True,source_rtl_sdc_or_synth_outputs_changed=False)
(r/'RECIP_AUTHENTIC_SYNTH_LOG_JOIN.json').write_text(json.dumps(rec,indent=2)+'\n')
om=K.manifest(str(s),runner=str(s/'run_kit_kv.sh'));nm=K.manifest(str(c),runner=str(c/'run_kit_kv.sh'));d=K.decide(nm,om)
(r/'recip_source_manifest_logjoin.json').write_text(json.dumps(om,indent=1)+'\n');(r/'recip_decision_logjoin.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
