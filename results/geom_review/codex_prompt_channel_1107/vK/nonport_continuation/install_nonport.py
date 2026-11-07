from pathlib import Path
import hashlib,json,shutil
root=Path('/srv/opentallas-scratch2/claude/codex-kv-prompt-0615');k=root/'qkd_hr_core_prompt_vK';pkg=root/'holdscope_1369d2ba06'
original=(k/'run_kit_kv.sh').read_text();assert original.count('-e HUID=$(id -u)')==1
s=original.replace('-e HUID=$(id -u)','-e OT_HOLD_REPAIR_SCOPE=nonport -e OT_HOLD_SCOPE_KEEP_SDC=1 -e HUID=$(id -u)')
s=s.replace('$K/run_$GOAL.log','$K/run_${GOAL}_nonport.log')
assert s!=original
(k/'run_kit_kv_nonport.sh').write_text(s)
for n in ('orfs_hold_mm.py','orfs_hold_mm.tcl'):shutil.copyfile(pkg/'tools'/n,k/n)
m={'schema':'opentallas.flow_class_continuation.v1','source_commit':'1369d2ba06','scope':'nonport','excluded_hold':'input-start only during repair; outputs/macros/internal retained; exact FF SDC restored','original_4_cts_sha256':(root/'vK_stale_mm_attempt/4_cts.sha256').read_text().split()[0],'old_attempt':str(root/'vK_stale_mm_attempt'),'new_runner':str(k/'run_kit_kv_nonport.sh'),'new_log':str(k/'run_grt_nonport.log'),'proof_inputs':'RTL/config/lec.py unchanged; original proof owner retained','files':{n:hashlib.sha256((k/n).read_bytes()).hexdigest() for n in ('orfs_hold_mm.py','orfs_hold_mm.tcl','run_kit_kv_nonport.sh')}}
(k/'NONPORT_FLOW_CONTINUATION.json').write_text(json.dumps(m,indent=2)+'\n');print(json.dumps(m))
