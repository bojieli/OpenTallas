from pathlib import Path
import subprocess,os
r=Path.cwd();img='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
cmd="""set -eu
L=/w/libs
LIBS=''
for f in $L/asap7sc7p5t_{AO,INVBUF,OA,SEQ,SIMPLE}_RVT_TT_nldm_*.lib*; do LIBS="$LIBS --liberty $f"; done
python3 tools/ref_tile/native_census_current.py --netlist mapped.v --top ot_hbm_svc_wb_kport_q --out native_current.json $LIBS --liberty physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_tt.lib
"""
with (r/'native_current.log').open('w') as f:rc=subprocess.run(['docker','run','--rm','-u',f'{os.getuid()}:{os.getgid()}','-v',str(r)+':/w','-w','/w','--entrypoint','bash',img,'-c',cmd],stdout=f,stderr=subprocess.STDOUT).returncode
print('CURRENT_NATIVE_ONLY_RC',rc,flush=True)
raise SystemExit(rc)
