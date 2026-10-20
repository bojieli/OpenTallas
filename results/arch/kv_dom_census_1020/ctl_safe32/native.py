from pathlib import Path
import subprocess,json
root=Path.cwd();src=Path('/srv/opentallas-scratch/claude/ref_gate/qkd_kvs_ctl_mu6c-20261019-230301/src')
libs=sorted(root.glob('*.lib'))+sorted((src/'physical/asap7_memory_macros_v2').glob('ctl_sram*/*_tt.lib'))
cmd=['python3',str(root/'tools/ref_tile/native_census.py'),'--netlist',str(root/'qkd_kvs_ctl_s32.mapped.v'),'--top','qkd_kvs_ctl_s32','--out',str(root/'native_census.json')]
for p in libs:cmd+=['--liberty',str(p)]
(root/'native_inputs.json').write_text(json.dumps(dict(tool_commit='94de8573f',argv=cmd),indent=2)+'\n')
raise SystemExit(subprocess.call(cmd))
