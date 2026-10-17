#!/usr/bin/env python3
"""All128 storage + actual four stack V producers, component boundary inputs."""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
ISSUER='rtl/hdc/nearhbm/ot_qwen_tp8_vrow_stack_static.sv';REV='9251d9e4e'
SOURCES=['rtl/qwen_sys/static_kv_20261014/qkd_static_kv_frame.sv',
 'rtl/qwen_sys/static_kv_20261014/qkd_static_kv_landing.sv','rtl/qwen_sys/static_kv_20261014/qkd_static_kv_hop.sv',
 'rtl/test/qwen_static_kv/tb_qkd_frame_four_stack_full128.sv',
 'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',ISSUER]

def prepare(out):
    out.mkdir(parents=True,exist_ok=False);manifest={};origin={}
    for p in SOURCES:
        source=ROOT/p
        if p==ISSUER:
            data=subprocess.check_output(['git','show',REV+':'+p],cwd=ROOT);origin[p]=REV
        else:data=source.read_bytes();origin[p]='current tracked candidate'
        d=out/'source'/p;d.parent.mkdir(parents=True,exist_ok=True);d.write_bytes(data)
        manifest[p]=hashlib.sha256(data).hexdigest()
    (out/'source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (out/'source_origin.json').write_text(json.dumps(origin,indent=2)+'\n');shutil.copy2(__file__,out/'execute.py')

def execute(out,mutants):
    manifest=json.loads((out/'source_manifest.json').read_text())
    for p,s in manifest.items():
        if hashlib.sha256((out/'source'/p).read_bytes()).hexdigest()!=s:raise RuntimeError('source changed '+p)
    sources=[str(out/'source'/p) for p in manifest];runs=[];top='tb_qkd_frame_four_stack_full128'
    for mut in (range(4) if mutants else [0]):
        obj=out/f'obj{mut}'
        with (out/f'build{mut}.log').open('w') as log:
            subprocess.run(['verilator','--binary','--timing','-Wno-fatal','-j','4','--top-module',top,f'-GMUT={mut}','--Mdir',str(obj),*sources],stdout=log,stderr=subprocess.STDOUT,check=True)
        r=subprocess.run([str(obj/('V'+top))],capture_output=True,text=True)
        text=r.stdout+r.stderr;(out/f'm{mut}.log').write_text(text)
        good=r.returncode==0 and 'PASS actual4 V issuers/all128PC' in text
        rejected=r.returncode!=0 and 'FULL128_FAIL' in text
        runs.append(dict(mut=mut,returncode=r.returncode,pass_observed=good,mutant_rejected=rejected,
           measure=next((x for x in text.splitlines() if x.startswith('MEASURE')),None)))
        if (not good if mut==0 else not rejected):
            (out/'partial.json').write_text(json.dumps(runs,indent=2)+'\n');raise RuntimeError('gate failed '+str(mut))
    report=dict(status='PASS_ALL128_FULLFRAME_ACTUAL4V_COMPONENT',source_sha256=manifest,
      gate_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),runs=runs,
      PCs=128,physical_SRAM_macros=512,frames=36,sectors_per_PC_frame=512,
      four_stack_rows=8192,four_stack_issue_edges=2048,test_frame_core_edges=3040,
      test_frame_vs_immutable2190=3040/2190,production_installable=False,physical_qualified=False,
      limitation='External declared SRAM-write and EXP-zero storage-boundary stimuli; actual issuers and memories only inside DUT. No native writer/EP/PV arithmetic, all128 controller/clock/physical,2190 attention frame or token qualification.')
    (out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--prepare-only',action='store_true');p.add_argument('--execute-only',action='store_true');p.add_argument('--mutants',action='store_true');a=p.parse_args();a.out=a.out.resolve()
    if not a.execute_only:prepare(a.out)
    if not a.prepare_only:execute(a.out,a.mutants)
