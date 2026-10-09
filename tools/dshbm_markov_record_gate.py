#!/usr/bin/env python3
"""Minimum real native CP/record/SMH numerical gate and weight-line mutant."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
SOURCES=[
 'rtl/test/ot_hdc_prefix_sim.sv',
 'rtl/v41rom/ot_v41_bterm.sv','rtl/v41rom/ot_v41_bterm2.sv',
 'rtl/gpu/ot_gpu_fadd.sv','rtl/hdc/ot_hdc_fp32_add_lat.sv','rtl/hdc/ot_hdc_fp32_mul_lat.sv',
 'rtl/hdc/ot_hdc_fastfp.sv','rtl/gpu/ot_gpu_tree.sv','rtl/gpu/ot_gpu_issue.sv',
 'rtl/gpu/ot_gpu_stack.sv','rtl/gpu/ot_gpu_tc_col.sv','rtl/gpu/ot_gpu_bd_col.sv',
 'rtl/hdc/v41/ot_hdc_blockdot.sv','rtl/gpu/ot_gpu_bulk_copy.sv','rtl/gpu/ot_gpu_sm_v.sv',
 'rtl/hdc/ot_hdc_fpu.sv','rtl/hdc/ot_hdc_fp32_mul_pipe.sv','rtl/proto/ot_fp32_add_rne_pipe.sv',
 'rtl/hdc/ot_hdc_sfu.sv','rtl/hdc/ot_hdc_delay.sv',
 'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v',
 'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',
 'rtl/hbm_accel/epilogue/ot_hbm_accel_issue.sv','rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv',
 'physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v',
 'rtl/hbm_accel/sm/ot_hbm_accel_tc16.sv','rtl/hbm_accel/sm/ot_hbm_accel_bd_col.sv',
 'rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv','rtl/hbm_accel/sm/ot_hbm_accel_issue_pq.sv',
 'rtl/hbm_accel/sm/ot_hbm_accel_sm_pq.sv','rtl/hbm_accel/sm/ot_hbm_accel_stack.sv',
 'rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy_oq4.sv','rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy_oq5.sv',
 'rtl/hbm_accel/sm/ot_hbm_accel_smh_bd.sv','rtl/hbm_accel/sm/ot_hbm_accel_smh.sv',
 'rtl/hbm_accel/control_20261007/ot_hbm_sm_seq_ingress.sv',
 'rtl/hbm_accel/control_20261007/ot_hbm_sm_serial_owner.sv',
 'rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20.sv',
 'rtl/lib/ot_async_fifo.sv','rtl/lib/ot_reset_sync.sv',
 'rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv',
 'rtl/hbm_accel/control/ot_hbm_native_mtp_score_join_mx1.sv',
 'rtl/hbm_accel/control/ot_hbm_native_mtp_rank_argmax_mx1.sv',
 'rtl/hbm_accel/control/ot_hbm_native_mtp_smh_pc_dispatch_mx1.sv',
 'rtl/test/hbm_accel/tb_dshbm_markov_record_join.sv']

def run(payload,out):
    payload,out=Path(payload),Path(out);out.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((payload/'payload.json').read_text())
    if manifest['released_shard_sha256']!='e625902027b9d23d416f8818c665fab4704e0b96dc1bc778321601b700475a9d':
        raise ValueError('released native matrix payload required')
    for item in manifest['artifacts'].values():
        if hashlib.sha256((payload/item['path']).read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('native payload changed')
    evidence=[]
    for mutant in (False,True):
        tag='weight_mutant' if mutant else 'positive';exe=out/(tag+'.vvp')
        cmd=['iverilog','-g2012','-s','tb_dshbm_markov_record_join','-o',str(exe)]
        if mutant:cmd+=['-DMUTATE_WEIGHT']
        cmd += [str(ROOT/p) for p in SOURCES]
        with (out/(tag+'.compile.log')).open('w') as f:
            c=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
        if c.returncode:raise RuntimeError('compile failed '+tag)
        with (out/(tag+'.log')).open('w') as f:
            r=subprocess.run(['vvp',str(exe),'+DIR='+str(payload)],stdout=f,stderr=subprocess.STDOUT)
        log=(out/(tag+'.log')).read_text()
        if not mutant and (r.returncode or 'PASS actual CP record SMH' not in log):raise RuntimeError('actual native numerical gate failed')
        if mutant and (r.returncode==0 or 'MISMATCH row=' not in log):raise RuntimeError('weight mutation not caught numerically')
        evidence.append(dict(name=tag,returncode=r.returncode,log=tag+'.log'))
    result=dict(status='PASS',scope='actual CP + typed native record + real serial owner + SMH released43x256 Markov + nonzero stored logits +0.9GHz LAT3 score add + local43-row argmax',
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
        payload=manifest,runs=evidence,whole_token_qualified=False,
        missing=['production native DHEAD source capture','rank-ordered full129280 argmax','actual full11kernel installed provider'],
        prefix='same SAT-proved behavioral prefix stand-in used by retained fullshape SM proof',
        physical_qualified=False)
    (out/'verdict.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--payload',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();r=run(a.payload,a.out);print(json.dumps(dict(status=r['status'],scope=r['scope'])))
