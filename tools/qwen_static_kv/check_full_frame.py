#!/usr/bin/env python3
"""Actual full512 SRAM group storage proof, no reference data inside DUT."""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['rtl/qwen_sys/static_kv_20261014/qkd_static_kv_frame.sv',
 'rtl/qwen_sys/static_kv_20261014/qkd_static_kv_landing.sv',
 'rtl/qwen_sys/static_kv_20261014/qkd_static_kv_hop.sv',
 'rtl/test/qwen_static_kv/tb_qkd_static_kv_frame.sv',
 'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v']

def prepare(out):
    out.mkdir(parents=True,exist_ok=False)
    for p in SOURCES:
        d=out/'source'/p;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/p,d)
    (out/'source_manifest.json').write_text(json.dumps({p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},indent=2)+'\n')
    shutil.copy2(__file__,out/'execute.py')

def execute(out):
    manifest=json.loads((out/'source_manifest.json').read_text())
    for p,s in manifest.items():
        if hashlib.sha256((out/'source'/p).read_bytes()).hexdigest()!=s:raise RuntimeError('source changed '+p)
    sources=[str(out/'source'/p) for p in manifest];runs=[];top='tb_qkd_static_kv_frame'
    for mut in range(4):
        obj=out/f'obj{mut}'
        with (out/f'build{mut}.log').open('w') as f:
            subprocess.run(['verilator','--binary','--timing','-Wno-fatal','-j','2','--top-module',top,f'-GMUT={mut}','--Mdir',str(obj),*sources],stdout=f,stderr=subprocess.STDOUT,check=True)
        r=subprocess.run([str(obj/('V'+top))],capture_output=True,text=True)
        text=r.stdout+r.stderr;(out/f'm{mut}.log').write_text(text)
        passed=r.returncode==0 and 'PASS full512 mapped-SRAM' in text
        rejected=r.returncode!=0 and 'FRAME_FAIL' in text
        runs.append(dict(mut=mut,returncode=r.returncode,pass_observed=passed,mutant_rejected=rejected,
          measure=next((l for l in text.splitlines() if l.startswith('MEASURE')),None)))
        if (not passed if mut==0 else not rejected):
            (out/'partial.json').write_text(json.dumps(runs,indent=2)+'\n');raise RuntimeError('frame gate failed '+str(mut))
    report=dict(status='PASS_FULL512_COMPONENT_STORAGE',source_sha256=manifest,runs=runs,
      gate_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      sectors_per_pc=512,physical_quarters=4,layers=36,physical_macros=16,
      clock='actual single-clock catalog SRAM, CORE domain after real CDC ring',
      data_transport_edges=7,production_installable=False,physical_qualified=False,
      limitation='Declared storage-boundary stimuli. Actual reader+ring+native four-stack V/PV/EXP composition and physical slot remain separate required gates.')
    (out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--prepare-only',action='store_true');p.add_argument('--execute-only',action='store_true');a=p.parse_args();a.out=a.out.resolve()
    if not a.execute_only:prepare(a.out)
    if not a.prepare_only:execute(a.out)
