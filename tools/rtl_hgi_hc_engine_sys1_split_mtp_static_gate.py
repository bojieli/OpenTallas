#!/usr/bin/env python3
"""Actual SRAM to projection to HC tail composition, fixed calendar and mutants."""
import hashlib,json,subprocess,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import hdc_golden_v41 as G
import rtl_hdc_v41x_hcp_campaign as hc

def main():
    run=ROOT/'run_hc_sys1_split_mtp';run.mkdir(exist_ok=True)
    rng=np.random.default_rng(20261015)
    G.set_arith('chunk8')
    c=hc.synth_case('production K20480, 24rows',rng,20480,24,8,1,'typical',{'fn_std':.001,'x_std':1.})
    w=c['fn'].view(np.uint32).reshape(24,80,32,8).transpose(0,3,1,2)
    x=(c['x'].view(np.uint32)>>16).reshape(8,80,32,8).transpose(3,0,1,2)
    np.savetxt(run/'hc_static_w.mem',w.reshape(-1),fmt='%08x')
    np.savetxt(run/'hc_static_x.mem',x.reshape(-1),fmt='%04x')
    np.savetxt(run/'hc_static_exp.mem',c['exp'].view(np.uint32).reshape(-1),fmt='%08x')
    mixes=c['exp']
    bases=np.repeat(rng.normal(0,1,(1,24)).astype(G.F),8,axis=0)
    scales=np.repeat(rng.uniform(.1,2,(1,3)).astype(G.F),8,axis=0)
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
    for name,a in [('base',bases[:1]),('scale',scales[:1]),('tail_exp',np.array(expected))]:
        np.savetxt(run/f'engine_{name}.mem',a.view(np.uint32).reshape(-1),fmt='%08x')
    files=['rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_engine_sys1_split_mtp_static.sv',
        'rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_tail_static.sv',
        'rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_projection_sys1_split_static.sv',
        'rtl/hbm_accel/generic/peers/static_hc/ot_hdc_v41x_hcp_sys1_static.sv',
        'rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_weight_quarter_static.sv',
        'rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_residual_half_static.sv',
        'rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_bank_control_static.sv',
        'rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_aperture_static.sv',
        'rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv',
        'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v',
        'rtl/hdc/ot_hdc_prefix.sv','rtl/hdc/ot_hdc_fp32_add_lat.sv','rtl/hdc/ot_hdc_fp32_mul_lat.sv','rtl/hdc/ot_hdc_fastfp.sv','rtl/hdc/ot_hdc_fastfp_lat.sv','rtl/hdc/ot_hdc_delay.sv',
        'rtl/hdc/ot_hdc_sfu.sv','rtl/hdc/v41x/ot_hdc_v41x_hcp.sv',
        'rtl/hdc/v41x/ot_hdc_v41x_sfu.sv','rtl/hdc/v41/ot_hdc_fdiv.sv',
        'rtl/hdc/v41/ot_hdc_sinkhorn.sv','rtl/hdc/v41/ot_hdc_sk_arith.sv',
        'rtl/hdc/v41/ot_hdc_sk_recip_rom.sv','rtl/test/tb_hgi_hc_engine_sys1_split_mtp_static.sv',
        'rtl/test/hgi_hc_engine_sys1_split_mtp_static_harness.cpp']
    pins=files+['tools/hdc_golden.py','tools/hdc_golden_v41.py','tools/rtl_hgi_hc_engine_sys1_split_mtp_static_gate.py','tools/rtl_hdc_v41x_hcp_campaign.py']
    receipt={'scope':'actual SYS1 32weightquarter16residualhalf8control32LG8MAC plus actualtail, equalphase functional roots; no physical/native wholechip qualification','SYS_LAT_candidate':86,'leaf_source_status':'requires frozen physical-owner proof before launch','projection_clock_pins':91,'residual_write_edge_delta':1,
        'source_sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in pins},
        'fixture_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in run.glob('*.mem')},
        'K':20480,'positions':[6,8],'projection_rows':24,'tail_words_per_position':24,'sink_clock_divisor':7,'nominal_row_result_ages':[342+160*p for p in range(8)],'nominal_row_periods':{'6':1153,'8':1473},'early_row_result_ages':[322+160*p for p in range(8)],'early_row_periods':{'6':1133,'8':1453}}
    (run/'source.json').write_text(json.dumps(receipt,indent=2)+'\n')
    with (run/'build.log').open('w') as log:
        subprocess.run(['verilator','--cc','--exe','--build','-j','4','-O1','-Wno-fatal','-Wno-WIDTH','-Wno-TIMESCALEMOD',
            '--output-split','10000','--top-module','tb_hgi_hc_engine_sys1_split_mtp_static','-Mdir',str(run/'obj'),*[str(ROOT/f) for f in files]],
            cwd=run,stdout=log,stderr=subprocess.STDOUT,check=True)
    exe=run/'obj/Vtb_hgi_hc_engine_sys1_split_mtp_static'
    from concurrent.futures import ThreadPoolExecutor
    def simulate(item):
        name,args=item
        p=subprocess.run([str(exe),*args],cwd=run,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        (run/f'{name}.log').write_text(p.stdout)
        return name,p
    cases=[('exact6',['+NPOS=6']),('exact8',['+NPOS=8']),('exact_early6',['+NPOS=6','+EARLY']),('exact_early8',['+NPOS=8','+EARLY']),('mutant8',['+NPOS=8','+EARLY','+MUTANT'])]
    with ThreadPoolExecutor(max_workers=5) as pool:
        verdicts=list(pool.map(simulate,cases))
    for name,p in verdicts:
        print(name,p.returncode,p.stdout[-1800:],flush=True)
        receipt[name]={'exit_code':p.returncode,'log_sha256':hashlib.sha256(p.stdout.encode()).hexdigest()}
    (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    if any(p.returncode for name,p in verdicts if name.startswith('exact')):raise SystemExit('positive failed; mutant unqualified')
    if any(not p.returncode for name,p in verdicts if name.startswith('mutant')):raise SystemExit('mutant escaped')
if __name__=='__main__':main()
