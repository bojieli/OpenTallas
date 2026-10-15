#!/usr/bin/env python3
"""Actual FP RTL + 80 mapped SRAMs, K20480/24-row component gate.

Fixed 180/340 raw-pop slots are diagnostic calendar prices, not unit or chip
qualification. In particular this does not instantiate HC sigmoid/Sinkhorn.
"""
import hashlib,json,subprocess,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import rtl_hdc_v41x_hcp_campaign as hc

def main():
    run=ROOT/'run_hc_static';run.mkdir(exist_ok=True)
    hc.G.set_arith('chunk8')
    c=hc.synth_case('production K20480, 24rows',np.random.default_rng(20261015),20480,24,1,1,'typical',{'fn_std':.001,'x_std':1.})
    w=c['fn'].view(np.uint32).reshape(24,80,32,8).transpose(0,3,1,2)
    x=(c['x'].view(np.uint32)>>16).reshape(80,32,8).transpose(2,0,1)
    np.savetxt(run/'hc_static_w.mem',w.reshape(-1),fmt='%08x')
    np.savetxt(run/'hc_static_x.mem',x.reshape(-1),fmt='%04x')
    np.savetxt(run/'hc_static_exp.mem',c['exp'].view(np.uint32).reshape(-1),fmt='%08x')
    files=['rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_projection_static.sv',
        'rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_aperture_static.sv',
        'rtl/hdc/v41x/ot_hdc_v41x_hcp.sv','rtl/hdc/ot_hdc_fastfp.sv',
        'rtl/hdc/v41/ot_hdc_fdiv.sv','rtl/hdc/ot_hdc_delay.sv','rtl/hdc/ot_hdc_sfu.sv',
        'rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv',
        'rtl/test/tb_hgi_hc_projection_static.sv','rtl/test/hgi_hc_projection_static_harness.cpp']
    receipt={'scope':'actual arithmetic + mapped SRAM production-shape component; not full HC/throughput/physical qualification',
        'source_sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files},
        'K':20480,'rows':24,'raw_read_slots':[180,340],'row_command_period_cycles':681}
    (run/'source.json').write_text(json.dumps(receipt,indent=2)+'\n')
    cmd=['verilator','--cc','--exe','--build','-j','4','-O1','-Wno-fatal','-Wno-WIDTH',
        '-Wno-TIMESCALEMOD','--output-split','10000','--output-split-cfuncs','100',
        '--top-module','tb_hgi_hc_projection_static','-Mdir',str(run/'obj'),
        *[str(ROOT/f) for f in files]]
    with (run/'build.log').open('w') as log:
        subprocess.run(cmd,cwd=run,stdout=log,stderr=subprocess.STDOUT,check=True)
    exe=run/'obj/Vtb_hgi_hc_projection_static'
    for name,args in [('exact',[]),('mutant',['+MUTANT'])]:
        p=subprocess.run([str(exe),*args],cwd=run,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        (run/f'{name}.log').write_text(p.stdout)
        print(name,p.returncode,p.stdout[-1200:],flush=True)
        receipt[name]={'exit_code':p.returncode,'log_sha256':hashlib.sha256(p.stdout.encode()).hexdigest()}
        (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        if name=='exact' and p.returncode:raise SystemExit('positive gate failed; no mutant qualification')
        if name=='mutant' and not p.returncode:raise SystemExit('mutant escaped')
if __name__=='__main__':main()
