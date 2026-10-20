from pathlib import Path
import subprocess
R=Path('/srv/opentallas-scratch/claude/codex-xs-exact-native-1020')
image='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
std='/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/'
libs=[]
for corner in ['TT','FF']:
 for group,stamp,ext in [('AO','211120','.lib.gz'),('INVBUF','220122','.lib.gz'),('OA','211120','.lib.gz'),('SEQ','220123','.lib'),('SIMPLE','211120','.lib.gz')]:
  libs.append(std+f'asap7sc7p5t_{group}_RVT_{corner}_nldm_{stamp}{ext}')
for corner in ['tt','ff']:
 for macro in ['ot_sram_1r1w_128x256_m1_r2c2_p192_mir','ot_sram_1r1w_32x128_m1_p192_rc']:
  libs.append('/src/physical/asap7_memory_macros/'+macro+'/'+macro+'_'+corner+'.lib')
rcs=[]
for variant,stamp in [('d','013205'),('e','013206')]:
 gate=Path('/srv/opentallas-scratch/claude/ref_gate')/f'smh_xs_p192{variant}_lattice-20261020-{stamp}'
 mapped='/frozen/routes/gate/work/orfs/results/asap7/opentallas_ot_hbm_accel_smh_xs_asap7_ref_gate/base/1_2_yosys.v'
 cmd=['docker','run','--rm','--entrypoint','python3','-v',str(R)+':/audit','-v',str(gate)+':/frozen:ro','-v',str(gate/'src')+':/src:ro',image,'/audit/tools/ref_tile/native_census.py','--netlist',mapped,'--top','ot_hbm_accel_smh_xs','--out','/audit/'+variant+'_native32.json']
 for lib in libs:cmd.extend(['--liberty',lib])
 with (R/(variant+'_native32.log')).open('w') as f:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
 rcs.append(rc);print(variant,rc,(R/(variant+'_native32.log')).read_text(),flush=True)
raise SystemExit(max(rcs))
