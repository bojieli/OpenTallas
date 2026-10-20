# HBM-SMATT9 r7a: audit-only rerun on r6c 5_1_grt (no stage re-run). Fixes the two r6c audit invocations
# (PG asserted before final global_connect; mapped-netlist census applied to a post-CTS netlist) and adds
# sequential reach, CTS insertion/spread (ck_insertion.py, TT+FF) and sign-off-period TT setup / FF hold.
from pathlib import Path
import subprocess,json
r=Path('/srv/opentallas-scratch/claude/pvm9-r6-1020');A=r/'r7a';inv=r/'stage_inventory'
img='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
orbin='/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad'
D='opentallas_ot_hbm_sm_pv_merge_distributed_asap7_ref_gate'
base=r/'bf/work/results/asap7'/D/'base';odb='/base/5_1_grt.odb'
mac='/src/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2_p192_mir/ot_sram_1r1w_64x512_m1_r2c2_p192_mir_%s.lib'
def run(name,cmd,e):
 b=['docker','run','--rm','-v',str(r/'src')+':/src:ro','-v',str(base)+':/base:ro','-v',str(A)+':/a','-e','R7_ODB='+odb]
 for k,v in e.items():b+=['-e',k+'='+v]
 with (inv/('r7a_'+name+'.log')).open('w') as f:rc=subprocess.run(b+['--entrypoint',orbin,img]+cmd,stdout=f,stderr=subprocess.STDOUT).returncode
 print(name,rc,flush=True);return rc
run('pg_audit2',['-exit','-no_init','/a/pg_audit2.tcl'],{})
run('fanout',['-exit','-no_init','-python','/a/fanout_audit.py'],{'R7_OUT':'/a/post_grt_fanout.json'})
run('seqreach',['-exit','-no_init','-python','/a/sequential_reach.py'],{'AUDIT_ODB':odb,'AUDIT_OUT':'/a/post_grt_sequential_reach.json'})
for c,l in (('TT','tt'),('FF','ff')):
 run('sta_'+c,['-exit','-no_init','/a/sta_corner.tcl'],{'R7_CORNER':c,'R7_MACRO_LIB':mac%l,'R7_SDC':'/base/5_1_grt.sdc'})
with (inv/'r7a_ck_insertion.log').open('w') as f:
 rc=subprocess.run(['python3',str(A/'ck_insertion.py'),'--base',str(base),'--clock','core_clk','--image',img,'--route-corner','TT','--output',str(A/'ck_insertion.json')],stdout=f,stderr=subprocess.STDOUT).returncode
print('ck_insertion',rc,flush=True)
print('R7A_DONE',flush=True)
