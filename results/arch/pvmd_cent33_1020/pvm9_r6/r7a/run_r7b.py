import subprocess
from pathlib import Path
r=Path('/srv/opentallas-scratch/claude/pvm9-r6-1020');A=r/'r7a'
img='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
base=r/'bf/work/results/asap7/opentallas_ot_hbm_sm_pv_merge_distributed_asap7_ref_gate/base'
b=['docker','run','--rm','-v',str(r/'src')+':/src:ro','-v',str(base)+':/base:ro','-v',str(A)+':/a','-e','R7_ODB=/base/5_1_grt.odb','-e','R7_SDC=/base/5_1_grt.sdc','-e','R7_MACRO_LIB=/src/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2_p192_mir/ot_sram_1r1w_64x512_m1_r2c2_p192_mir_ff.lib','--entrypoint','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad',img,'-exit','-no_init','/a/sta_ff2.tcl']
with open(r/'stage_inventory/r7b_sta_ff2.log','w') as f:print('sta_ff2',subprocess.run(b,stdout=f,stderr=subprocess.STDOUT).returncode)
