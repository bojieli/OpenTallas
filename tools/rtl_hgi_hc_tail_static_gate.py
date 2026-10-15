#!/usr/bin/env python3
"""Actual HC tail arithmetic, compiler operation/capture calendar and mutants."""
import hashlib,json,subprocess,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import hdc_golden_v41 as G

def main():
    run=ROOT/'run_hc_tail';run.mkdir(exist_ok=True)
    rng=np.random.default_rng(20261015)
    mixes=rng.normal(0,2,(16,24)).astype(G.F)
    bases=rng.normal(0,1,(16,24)).astype(G.F)
    scales=rng.uniform(.1,2,(16,3)).astype(G.F)
    expected=[]
    for m,b,s in zip(mixes,bases,scales):
        pre=G.add(G.sigmoid(G.add(G.mul(m[:4],s[0]),b[:4])),G.F(1e-6))
        post=G.mul(G.sigmoid(G.add(G.mul(m[4:8],s[1]),b[4:8])),G.F(2))
        c=G.add(G.mul(m[8:],s[2]),b[8:]).reshape(4,4)
        e=G.exp(G.add(c,G.neg(np.max(c,axis=1,keepdims=True))))
        c=G.add(G.div(e,G.seqsum([e[:,k] for k in range(4)])[:,None]),G.F(1e-6))
        def cols(x):return G.div(x,G.add(G.seqsum([x[k,:] for k in range(4)]),G.F(1e-6))[None,:])
        def rows(x):return G.div(x,G.add(G.seqsum([x[:,k] for k in range(4)]),G.F(1e-6))[:,None])
        c=cols(c)
        for _ in range(19):c=cols(rows(c))
        expected.append(np.concatenate((pre,post,c.reshape(-1))))
    for name,a in [('mix',mixes),('base',bases),('scale',scales),('exp',np.array(expected))]:
        np.savetxt(run/f'tail_{name}.mem',a.view(np.uint32).reshape(-1),fmt='%08x')
    files=['rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_tail_static.sv',
        'rtl/hdc/ot_hdc_fastfp.sv','rtl/hdc/ot_hdc_fastfp_lat.sv','rtl/hdc/ot_hdc_delay.sv',
        'rtl/hdc/ot_hdc_sfu.sv','rtl/hdc/v41x/ot_hdc_v41x_hcp.sv',
        'rtl/hdc/v41x/ot_hdc_v41x_sfu.sv','rtl/hdc/v41/ot_hdc_fdiv.sv',
        'rtl/hdc/v41/ot_hdc_sinkhorn.sv','rtl/hdc/v41/ot_hdc_sk_arith.sv',
        'rtl/hdc/v41/ot_hdc_sk_recip_rom.sv','rtl/test/tb_hgi_hc_tail_static.sv',
        'rtl/test/hgi_hc_tail_static_harness.cpp']
    pins=files+['tools/hdc_golden.py','tools/hdc_golden_v41.py','tools/rtl_hgi_hc_tail_static_gate.py']
    receipt={'scope':'actual HC tail component fixed-calendar; not physical/native whole-chip qualification',
        'source_sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in pins},
        'fixture_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in run.glob('*.mem')},
        'cases':16,'words_per_case':24,'sink_clock_divisor':7,'sink_launch_age':217,'sink_capture_age':506,'result_age':507}
    (run/'source.json').write_text(json.dumps(receipt,indent=2)+'\n')
    with (run/'build.log').open('w') as log:
        subprocess.run(['verilator','--cc','--exe','--build','-j','4','-O1','-Wno-fatal','-Wno-WIDTH','-Wno-TIMESCALEMOD',
            '--output-split','10000','--top-module','tb_hgi_hc_tail_static','-Mdir',str(run/'obj'),*[str(ROOT/f) for f in files]],
            cwd=run,stdout=log,stderr=subprocess.STDOUT,check=True)
    exe=run/'obj/Vtb_hgi_hc_tail_static'
    for name,args in [('exact',[]),('mutant',['+MUTANT'])]:
        p=subprocess.run([str(exe),*args],cwd=run,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        (run/f'{name}.log').write_text(p.stdout)
        print(name,p.returncode,p.stdout[-1200:],flush=True)
        receipt[name]={'exit_code':p.returncode,'log_sha256':hashlib.sha256(p.stdout.encode()).hexdigest()}
        (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        if name=='exact' and p.returncode:raise SystemExit('positive failed; mutant unqualified')
        if name=='mutant' and not p.returncode:raise SystemExit('mutant escaped')
if __name__=='__main__':main()
