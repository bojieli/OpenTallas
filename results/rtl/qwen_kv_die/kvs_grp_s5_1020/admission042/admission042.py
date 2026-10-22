from pathlib import Path
import subprocess
p=Path('/srv/opentallas-scratch/claude/ref_gate/codex_s5_1020');base=p.parent/'qkd_kvs_grp_h_s4b-20261019-221603/src'
libs=sorted(p.glob('*.lib'))+[base/'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2_p192_mir/ot_sram_1r1w_128x256_m1_r2c2_p192_mir_tt.lib']
for t in ['qkd_kvs_grp_s5','qkd_kvs_grp_h_s5']:
 cmd=['python3',str(p/'admission042/tools/ref_tile/native_census.py'),'--netlist',str(p/(t+'.mapped.v')),'--top',t,'--out',str(p/(t+'.admission042.json'))]
 for lib in libs:cmd+=['--liberty',str(lib)]
 subprocess.run(cmd,check=True)
