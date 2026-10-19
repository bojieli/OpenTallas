from pathlib import Path
import json,subprocess
root=Path('/srv/opentallas-scratch/claude/codex-s81-dieplace');cand=root/'placement_diag/coll_safe2_parent';r=json.loads((cand/'bound2/bind/bind_case.json').read_text());cmd=r['port_bind_cmd'];cmd[2]=str(root/'bound_v2/bind/die.v')
for flag,file in [('--strap-file','straps.json'),('--pad-file','pads.json')]:cmd[cmd.index(flag)+1]=str(root/'bound_v2/bind'/file)
cmd[cmd.index('--out')+1]=str(cand/'baseline_current_binder.json')
# Drop only the new source-selector define: original die selects the unchanged legacy modules.
i=cmd.index('OT_S81PH_COLL_TF_CLEANUP');assert cmd[i-1]=='--define';del cmd[i-1:i+1]
(cand/'baseline_current_binder_cmd.json').write_text(json.dumps(cmd,indent=1)+'\n')
p=subprocess.run(cmd,capture_output=True,text=True);(cand/'baseline_current_binder.log').write_text(p.stdout+p.stderr);print('BASELINE_BIND_RC',p.returncode);print(p.stdout[-2200:])
