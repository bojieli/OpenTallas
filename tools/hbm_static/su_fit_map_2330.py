#!/usr/bin/env python3
"""Source-current SU heavy area diagnostics only; no new hardened master or timing qualification."""
import argparse,hashlib,json,os,pathlib,subprocess,sys
SOURCES = ['rtl/hbm_accel/generic/adapters/static_su/arithmetic/ot_hbm_su_static_ins.sv', 'rtl/hbm_accel/generic/adapters/static_su/arithmetic/ot_hbm_su_static_lane.sv', 'rtl/hbm_accel/generic/adapters/static_su/arithmetic/ot_hbm_su_static_arithmetic.sv', 'rtl/hdc/v41x/ot_hdc_v41x_sfu.sv', 'rtl/hdc/ot_hdc_delay.sv', 'rtl/hdc/ot_hdc_fpu.sv', 'rtl/hdc/ot_hdc_fp32_mul_pipe.sv', 'rtl/proto/ot_fp32_add_rne_pipe.sv', 'rtl/hdc/ot_hdc_sfu.sv', 'rtl/hdc/ot_hdc_fastfp.sv', 'rtl/hdc/ot_hdc_fastfp_lat.sv', 'rtl/hdc/ot_hdc_fp32_mul_lat.sv', 'rtl/hdc/ot_hdc_fp32_add_lat.sv', 'rtl/hdc/ot_hdc_prefix.sv', 'rtl/hdc/v41/ot_hdc_fsqrt.sv', 'rtl/hdc/v41/ot_hdc_fdiv.sv', 'rtl/hdc/v41/ot_hdc_softplus.sv', 'rtl/hbm_accel/generic/adapters/static_su/arithmetic/ot_hbm_su_static_lane_pinreg.sv', 'rtl/hbm_accel/generic/adapters/static_su/arithmetic/ot_hbm_su_static_side.sv']
p=argparse.ArgumentParser(description=__doc__);p.add_argument('kind',choices=['SFU','FULL','SIDE']);p.add_argument('out');a=p.parse_args()
out=pathlib.Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
top='ot_hbm_su_static_side' if a.kind=='SIDE' else 'ot_hbm_su_static_lane_pinreg'
cmd=[sys.executable,'tools/run_abi3_physical.py','--view','asap7','--clock-period-ns','1.111111111','--clock-uncertainty-ns','.060','--clock-uncertainty-hold-ns','.025','--stages','synth','--synth-timeout-seconds','unlimited','--flow-timeout-seconds','unlimited','--keep-workdir',str(out/'work'),'--output',str(out/'result.json'),'--top',top,'--clock-port','clk[0]' if a.kind=='SIDE' else 'clk_stage[0]']
if a.kind!='SIDE':
 for k,v in dict(KIND=1 if a.kind=='SFU' else 2,LN=7,MLAT=4,ALAT=3,LEAF=1,FETCH_EXTRA_EDGES=2,PIN_RST=1).items():cmd+=['--param',f'{k}={v}']
for src in SOURCES:cmd+=['--source',src]
(out/'command.json').write_text(json.dumps(cmd,indent=1)+'\n')
(out/'source.sha256.json').write_text(json.dumps({p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in SOURCES},indent=1)+'\n')
r=subprocess.run(cmd,env=dict(os.environ,OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='1'));sys.exit(r.returncode)
