#!/usr/bin/env python3
"""Source-pinned SU collective port component bench; execute through ot-run.

Real four pgslices, qcore and mapped SRAMs. A PASS here does not qualify a full
SU programme, physical relays, or the complete die. Completed objects may be
reused only with an identical source and elaboration manifest.
"""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
S='rtl/hbm_accel/generic/adapters/static_su/'
SOURCES=[S+p+'.sv' for p in ['arithmetic/ot_hbm_su_static_ins','arithmetic/ot_hbm_su_static_lane','arithmetic/ot_hbm_su_static_lane_pinreg','arithmetic/ot_hbm_su_static_side','data_store/ot_hbm_su_static_data_store','data_store/ot_hbm_su_static_pinned_bank','register_file/ot_hbm_su_static_rf','reduction/ot_hbm_su_reduce_static','ot_hbm_su_static_vm_ports','top/ot_hbm_su_static_pgslice','top/ot_hbm_su_static_qcore','programme/multirate_bridge']]
SOURCES+=['rtl/hdc/'+p+'.sv' for p in ['v41x/ot_hdc_v41x_sfu','ot_hdc_delay','ot_hdc_fpu','ot_hdc_fp32_mul_pipe','ot_hdc_sfu','ot_hdc_fastfp','ot_hdc_fastfp_lat','ot_hdc_fp32_mul_lat','ot_hdc_fp32_add_lat','ot_hdc_prefix','v41/ot_hdc_fsqrt','v41/ot_hdc_fdiv','v41/ot_hdc_softplus']]
SOURCES+=['rtl/proto/ot_fp32_add_rne_pipe.sv','physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',S+'collport/ot_hbm_su_static_cxport.sv',S+'collport/tb_hbm_su_collport.sv']
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--objdir',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--qid',type=int,default=1);ap.add_argument('--inj-ret',type=int,default=11);ap.add_argument('--sd',type=int,default=0)
    ap.add_argument('--mut-cx',type=int,default=0);ap.add_argument('--mut-pg',type=int,default=0);ap.add_argument('--mut-qc',type=int,default=0)
    ap.add_argument('--reuse-build',action='store_true');ap.add_argument('--jobs',type=int,default=8);a=ap.parse_args()
    obj=a.objdir.resolve();out=a.out.resolve();obj.mkdir(parents=True,exist_ok=True);out.mkdir(parents=True,exist_ok=True)
    params=dict(QID=a.qid,INJ_RET=a.inj_ret,SD=a.sd,MUT_CX=a.mut_cx,MUT_PG=a.mut_pg,MUT_QC=a.mut_qc)
    manifest=dict(sources={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SOURCES},params=params)
    mp=obj/'collport_build_manifest.json'
    if a.reuse_build:
        if not mp.exists() or json.loads(mp.read_text())!=manifest:raise ValueError('Completed objects do not match exact source/parameters')
    else:
        mp.write_text(json.dumps(manifest,indent=2)+'\n')
        cmd=['verilator','--binary','--timing','-j',str(a.jobs),'-O2','-CFLAGS','-O0','-Wno-fatal','-Wno-WIDTH','-Wno-TIMESCALEMOD','--output-split','20000','--top-module','tb_hbm_su_collport','-Mdir',str(obj)]
        cmd += ['-G'+k+'='+str(v) for k,v in params.items()]+SOURCES
        with (out/'build.log').open('w') as f:subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
    mutant=bool(a.mut_cx or a.mut_pg or a.mut_qc)
    cases=['positive'] if mutant else ['positive','PHASE2','COLLIDE']
    rows=[]
    for case in cases:
        p=subprocess.run([str(obj/'Vtb_hbm_su_collport')]+([] if case=='positive' else ['+'+case]),cwd=ROOT,capture_output=True,text=True)
        text=p.stdout+p.stderr;(out/(case+'.log')).write_text(text)
        if mutant:
            passed=p.returncode!=0 and ('SU_COLLPORT' in text or 'Assertion failed' in text)
        elif case=='positive':passed=p.returncode==0 and 'SU_COLLPORT PASS QID=' in text and 'SU_COLLPORT FAIL' not in text
        else:passed=p.returncode==0 and 'PASS negative control faulted' in text and 'SU_COLLPORT FAIL' not in text
        rows.append(dict(case=case,exit=p.returncode,expected_mutant_rejected=mutant,passed=passed))
        if not passed:raise RuntimeError(f'Gate failed: {case}; inspect {out}')
    receipt=dict(scope='SU collective port component only; full SU programme/physical/die qualification OPEN',manifest=manifest,cases=rows)
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print('SU_COLLPORT_GATE PASS')
if __name__=='__main__':main()
