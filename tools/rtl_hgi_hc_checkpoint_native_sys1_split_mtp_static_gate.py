#!/usr/bin/env python3
"""Actual SRAM to projection to HC tail composition, fixed calendar and mutants."""
import hashlib,json,subprocess,sys,re
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import hdc_golden_v41 as G
import rtl_hdc_v41x_hcp_campaign as hc
from lower_hbm_hc_sys1_mtp_static_calendar import lower_sys1 as lower
from lower_hbm_hc_native_sys1_component_calendar import lower_native_sys1 as lower_native

def analyze_structural_warnings(build):
    prefix=ROOT/'rtl/hdc/ot_hdc_prefix.sv'
    prefix_sha=hashlib.sha256(prefix.read_bytes()).hexdigest()
    if prefix_sha!='98f2492a22012ffbaae49ac8405c2af693e16cb7bcdfafc5eb66db7943240587':
        raise RuntimeError('prefix source differs from inspected level-directed DAG')
    # Every generated g[l+1]/p[l+1] assignment reads level l only. The
    # array-level Verilator warning collapses these distinct indexed nets.
    # Permit only the two exact closed LG8 multiplier prefix array signals.
    origin='tb_hgi_hc_checkpoint_native_sys1_split_mtp_static.dut.arithmetic.engine.projection.bank[0].mac[0].lanes.g_lane[0].u_mul.u_pw.'
    accepted=[]
    for line in build.splitlines():
        if line.startswith('%Warning-LATCH:') or line.startswith('%Warning-MULTIDRIVEN:'):
            raise RuntimeError(f'forbidden structural warning: {line}')
        if line.startswith('%Warning-UNOPTFLAT:'):
            match=re.fullmatch(r"%Warning-UNOPTFLAT: (.*):(\d+):(\d+): Signal unoptimizable: Circular combinational logic: '([^']+)'",line)
            legal=(match and match[1]==str(prefix) and match[3]=='27' and
                   (match[2],match[4]) in [('24',origin+'g'),('25',origin+'p')])
            if not legal:raise RuntimeError(f'unexplained UNOPTFLAT: {line}')
            accepted.append(line)
    if len(accepted)>2:raise RuntimeError('unexpected repeated prefix warnings')
    return {'accepted_indexed_prefix_headers':accepted,'source_sha256':prefix_sha,
        'reason':'g/p at level l+1 depend only on level l; no directed bit-level cycle. Exact source/line/signal match only; raw warnings preserved.',
        'all_other_UNOPTFLAT':0,'LATCH':0,'MULTIDRIVEN':0}

def main():
    import os,shutil
    command_native=1
    sys_latency=86
    sys_delta=sys_latency-33
    engine_path=Path(os.environ['HC_SYS1_ENGINE_RECEIPT'])
    engine=json.loads(engine_path.read_text())
    if engine.get('SYS_LAT_candidate')!=sys_latency or any(engine.get(k,{}).get('exit_code')!=0 for k in ('exact6','exact8','exact_early6','exact_early8')) or engine.get('mutant8',{}).get('exit_code',0)==0:
        raise RuntimeError('actual SYS1 arithmetic prerequisite has not passed')
    build_threads=int(os.environ.get('HC_BUILD_THREADS','4'))
    if build_threads<1:raise ValueError('positive build threads')
    if command_native not in (0,1):raise ValueError('HC_COMMAND_NATIVE0/1')
    run=ROOT/'run_hc_command_native_sys1_split_mtp';run.mkdir(exist_ok=False)
    compile_cache=os.environ.get('HC_SYS1_COMPILE_CACHE')
    if compile_cache:shutil.copytree(Path(compile_cache),run/'obj',copy_function=shutil.copy2)
    rng=np.random.default_rng(20261015)
    G.set_arith('chunk8')
    c=hc.synth_case('production K20480, 24rows',rng,20480,24,8,1,'typical',{'fn_std':.001,'x_std':1.})
    import os,shutil
    checkpoint=Path(os.environ['HC_CHECKPOINT_INPUT'])
    original=checkpoint/'fn-original-layout-fp32.bin'
    c['fn']=np.fromfile(original,dtype='<f4').reshape(24,20480)
    assert hashlib.sha256(original.read_bytes()).hexdigest()=='11c9abd39f35e3364aad812c3f2dcb9c5fa5cf71e0f837a1af684112a00f930c'
    c['exp']=np.stack([hc.golden_mixes(c['fn'],c['x'][p].reshape(4,-1),c['eps'])[2] for p in range(8)])
    # Reconstruct the off-chip sector image from exact original FP32 weights.
    sectors=c['fn'].view(np.uint32).reshape(24,80,32,8).transpose(0,3,1,2).reshape(24,8,320,8)
    (run/'all24rows.hex').write_text(''.join(''.join(f'{int(x):08x}' for x in words[::-1])+'\n' for words in sectors.reshape(-1,8)))
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
    for n in (6,8):
        tail_first=((7+24*((280+sys_delta+160*(n-1)))+15+6)//7)*7
        words,meta=lower_native(npos=n,first_row_consumer_cycle=7,first_tail_consumer_cycle=tail_first,sys_latency=sys_latency)
        (run/f'full_sys1_n{n}.mem').write_text(''.join(f'{w:064x}\n' for w in words))
        (run/f'full_sys1_n{n}.json').write_text(json.dumps(meta,indent=2)+'\n')
    files=['rtl/hbm_accel/loader/service_native/ot_hbm_svc_native_sector_owned_stack.sv',
        'rtl/hbm_accel/loader/service_native/ot_hbm_svc_native_stream_pc_lease.sv',
        'rtl/hbm_accel/loader/service_native/tb_hbm_svc_command_dram_pipeline_fixture.sv',
        'rtl/chip/ot_chip_v41x_hbm3e_phy.sv','rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv','rtl/hdc/kv/ot_hdc_hbm_model.sv',
        'rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_native_sys1_split_mtp_static.sv',
        'rtl/hbm_accel/generic/peers/hc_prefetch_static/ot_hgi_hc_prefetch_resident_static.sv',
        'rtl/hbm_accel/loader/service_native/ot_hbm_svc_prefetch_region_cdc.sv',
        'rtl/hbm_accel/ingest/ot_hbm_loader_kport_address.sv',
        'rtl/lib/ot_reset_sync.sv','rtl/lib/ot_async_fifo.sv',
        'rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_result_vm_static.sv',
        'rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_vm_gather_adapter_static.sv',
        'rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_gathered_mix_reader_static.sv',
        'rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_residual_vm_static.sv',
        'rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_tap.sv',
        'rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv',
        'rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_programmed_sys1_split_mtp_static.sv',
        'rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_programme_mtp_static.sv',
        'rtl/hbm_accel/generic/peers/ot_hgi_sfu_program_stripe_static.sv',
        'rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_engine_sys1_split_mtp_static.sv',
        'rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_tail_static.sv',
        'rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_projection_sys1_split_static.sv',
        'rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_bank_control_static.sv',
        'rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_weight_quarter_static.sv',
        'rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_residual_half_static.sv',
        'rtl/hbm_accel/generic/peers/static_hc/ot_hdc_v41x_hcp_sys1_static.sv',
        'rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv',
        'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v',
        'rtl/hdc/ot_hdc_fastfp.sv','rtl/hdc/ot_hdc_fastfp_lat.sv','rtl/hdc/ot_hdc_delay.sv',
        'rtl/hdc/ot_hdc_fp32_add_lat.sv','rtl/hdc/ot_hdc_fp32_mul_lat.sv','rtl/hdc/ot_hdc_prefix.sv',
        'rtl/hdc/ot_hdc_sfu.sv','rtl/hdc/v41x/ot_hdc_v41x_hcp.sv',
        'rtl/hdc/v41x/ot_hdc_v41x_sfu.sv','rtl/hdc/v41/ot_hdc_fdiv.sv',
        'rtl/hdc/v41/ot_hdc_sinkhorn.sv','rtl/hdc/v41/ot_hdc_sk_arith.sv',
        'rtl/hdc/v41/ot_hdc_sk_recip_rom.sv','rtl/test/tb_hgi_hc_checkpoint_native_sys1_split_mtp_static.sv',
        'rtl/test/hgi_hc_checkpoint_native_sys1_split_mtp_static_harness.cpp']
    pins=files+['tools/hdc_golden.py','tools/hdc_golden_v41.py','tools/rtl_hgi_hc_checkpoint_native_sys1_split_mtp_static_gate.py','tools/rtl_hdc_v41x_hcp_campaign.py','tools/lower_hbm_hc_mtp_static_calendar.py','tools/lower_hbm_hc_tail_loop_calendar.py','tools/lower_hbm_hc_sys1_mtp_static_calendar.py','tools/lower_hbm_hc_native_sys1_component_calendar.py']
    for f in set(pins)&set(engine['source_sha256']):
        if hashlib.sha256((ROOT/f).read_bytes()).hexdigest()!=engine['source_sha256'][f]:raise RuntimeError(f'engine source mismatch: {f}')
    receipt={'compile_cache_copied_from':compile_cache,'engine_receipt_sha256':hashlib.sha256(engine_path.read_bytes()).hexdigest(),'engine_sources_match':True,'status':'PREPARED_NOT_RUN', 'SYS_LAT':sys_latency,'additional_pipeline_cycles':sys_delta,'residual_base_scales':'synthetic fixture; actual checkpoint FN only','canonical_G25_P1_qualified':False,'projection_clock_pins':91,'arithmetic_clock_roots_with_sink':92,'leaf_source':'473756fb3','additional_residual_write_cycle':1,'additional_read_calendar_cycles':0,'clock_scope':'equalphase functional only; physical clock/pin/reach/timing qualification open','full_native_chip_qualified':False,'scope':'actual paged programme SRAM to SYS1 473756fb3 split32weightquarters/16residualhalves/8controls/32LG8MAC/core projection/tail; actual4SID32bankVM96SRAM and12LGtaps joined plus realresultVMwrites/readback; actual20GiB checkpoint PHY CDC staging128SRAM joined; only offchip PHY data model; no wholechip/physical qualification',
        'source_sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in pins},
        'fixture_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [*run.glob('*.mem'),run/'all24rows.hex']},
        'K':20480,'positions':[6,8],'projection_rows':24,'tail_words_per_position':24,'sink_clock_divisor':7,'checkpoint_fn_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'actual_SRAMs':306+128*command_native,'command_native':command_native,'build_threads':build_threads,'tail_configuration_words':497,'tail_programme_reconfigure_between_positions':False,'tail_body_period':497,'configuration_words_n6':1577+sys_delta,'configuration_words_n8':1897+sys_delta,'host_reconfigure_between_projection_and_tail':False,'PHY_model':('strict command-only offchipfixture canonical23edge; corrected owned-stacka7b86347d actualcontroller' if command_native else 'published request-level refresh-aware ot_chip_v41x_hbm3e_phy') ,'nominal_row_result_ages':[289+sys_delta+160*p for p in range(8)],'nominal_row_periods':{'6':1100+sys_delta,'8':1420+sys_delta},'early_row_result_ages':[269+sys_delta+160*p for p in range(8)],'early_row_periods':{'6':1080+sys_delta,'8':1400+sys_delta}}
    (run/'source.json').write_text(json.dumps(receipt,indent=2)+'\n')
    if os.environ.get('HC_SYS1_PREPARE_ONLY')=='1':
        print('HC_SYS1_PREPARED_NOT_RUN source/fixtures pinned; actual engine verdict required before launch',flush=True)
        return
    # Generate first, inspect structural diagnostics, then compile C++ only
    # after that check passes. Keep both phases in the original raw log.
    with (run/'build.log').open('w') as log:
        subprocess.run(['verilator','--cc','--exe','-j',str(build_threads),'-O1','-Wno-fatal','-Wno-WIDTH','-Wno-TIMESCALEMOD',
            f'-GCOMMAND_NATIVE={command_native}','--output-split','10000','--top-module','tb_hgi_hc_checkpoint_native_sys1_split_mtp_static','-Mdir',str(run/'obj'),*[str(ROOT/f) for f in files]],
            cwd=run,stdout=log,stderr=subprocess.STDOUT,check=True)
    build_log=(run/'build.log').read_text()
    receipt['structural_warning_analysis']=analyze_structural_warnings(build_log)
    (run/'structural_warnings.json').write_text(json.dumps(receipt['structural_warning_analysis'],indent=2)+'\n')
    with (run/'build.log').open('a') as log:
        subprocess.run(['make','-C',str(run/'obj'),'-f','Vtb_hgi_hc_checkpoint_native_sys1_split_mtp_static.mk','-j',str(build_threads)],
            cwd=run,stdout=log,stderr=subprocess.STDOUT,check=True)
    exe=run/'obj/Vtb_hgi_hc_checkpoint_native_sys1_split_mtp_static'
    from concurrent.futures import ThreadPoolExecutor
    def simulate(item):
        name,args=item
        p=subprocess.run([str(exe),*args],cwd=run,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        (run/f'{name}.log').write_text(p.stdout)
        return name,p
    cases=[('exact6',['+NPOS=6']),('exact8',['+NPOS=8']),('mutant6',['+NPOS=6','+WEIGHT_MUTANT']),('mutant8',['+NPOS=8','+WEIGHT_MUTANT'])]
    with ThreadPoolExecutor(max_workers=5) as pool:
        verdicts=list(pool.map(simulate,cases))
    for name,p in verdicts:
        print(name,p.returncode,p.stdout[-1800:],flush=True)
        receipt[name]={'exit_code':p.returncode,'log_sha256':hashlib.sha256(p.stdout.encode()).hexdigest()}
    current={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in pins}
    if current!=receipt['source_sha256']:raise RuntimeError('source changed during gate')
    receipt['source_hashes_match']=True
    receipt['status']='TERMINAL_SEE_CASE_VERDICTS'
    (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    if any('HC_CHECKPOINT_NATIVE_SYS1_SPLIT_MTP_DONE' not in p.stdout for name,p in verdicts if name.startswith('exact')):raise SystemExit('positive completion marker missing')
    if any('programmed row data/time mismatch' not in p.stdout for name,p in verdicts if name.startswith('mutant')):raise SystemExit('payload mutant rejected for an unexpected reason')
    if any(p.returncode for name,p in verdicts if name.startswith('exact')):raise SystemExit('positive failed; mutant unqualified')
    if any(not p.returncode for name,p in verdicts if name.startswith('mutant')):raise SystemExit('mutant escaped')
    receipt['status']='PASS_ACTUAL_SYS1_NATIVE_VM_COMPONENT_ONLY'
    (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
