#!/usr/bin/env python3
from pathlib import Path
import subprocess,os,json
R=Path('/srv/opentallas-scratch/claude/codex-xs-placed-1020')
img='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
for v,stamp in [('d','013205'),('e','013206')]:
 gate=Path('/srv/opentallas-scratch/claude/ref_gate')/f'smh_xs_p192{v}_lattice-20261020-{stamp}'
 odb='/frozen/routes/gate/work/orfs/results/asap7/opentallas_ot_hbm_accel_smh_xs_asap7_ref_gate/base/5_1_grt.odb'
 base=['docker','run','--rm','-v',str(R)+':/audit','-v',str(gate)+':/frozen:ro']
 reach=base+['-e','AUDIT_ODB='+odb,'-e','AUDIT_OUT=/audit/'+v+'_sequential_reach.json','--entrypoint','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad',img,'-exit','-python','/audit/sequential_reach.py']
 pg=base+['-e','OT_PG_AUDIT_ODB='+odb,'-e','OT_PG_AUDIT_REPORT=/audit/'+v+'_native_pg.json','--entrypoint','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad',img,'-exit','/audit/audit_native_pg.tcl']
 for name,cmd in [('sequential_reach',reach)]:
  with (R/(v+'_'+name+'.log')).open('w') as f:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
  print(v,name,rc,flush=True)
