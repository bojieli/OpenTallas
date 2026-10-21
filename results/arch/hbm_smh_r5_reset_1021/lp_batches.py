import os,sys,subprocess
from pathlib import Path
root=Path(__file__).parent;src=root/'src'
env=dict(os.environ,LP_ROOT=str(src),SIM='verilator',VL_JOBS='4')
rc=0
for f in [sys.argv[1]+'_m',sys.argv[1]+'_f']:
 out=root/('proof_'+f)
 one=subprocess.call(['bash',str(src/'rtl/hbm_accel/sm/repack/h2a5'/('lp_'+f)/('ot_hbm_smh_rp5'+f+'_bench.sh')),str(out)],env=env)
 print('LP_FORM_EXIT',f,one,flush=True);rc=max(rc,one)
raise SystemExit(rc)
