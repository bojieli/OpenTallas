from pathlib import Path
import json
k=Path('/srv/opentallas-scratch2/claude/codex-kv-prompt-0615/qkd_hr_core_prompt_vK')
p=k/'physical_completion/kvcore-qkd_hr_core_prompt_vK_-2601424.json';r=json.loads(p.read_text());assert r['goal']=='grt' and r['rc']==0 and (k/r['checkpoint']['path']).is_file()
s=(k/'run_kit_kv_nonport.sh').read_text();a='{ [ $GOAL = finish ] || [ $GOAL = route ]; }; then';assert s.count(a)==1
s=s.replace(a,'{ [ $GOAL = finish ]; }; then')
# Native `make route` depends on the current saved GRT checkpoint, with unchanged HOLD_SLACK_MARGIN=5.
# Skip only the wrapper's redundant pre-route cts/grt/HOLD_SLACK_MARGIN=0 re-entry after an already reviewed GRT.
s='# vK staged route from reviewed GRT; no pre-route cts/grt replay.\n'+s
(k/'run_kit_kv_after_grt.sh').write_text(s)
print('staged route runner prepared from',r['checkpoint']['path'])
