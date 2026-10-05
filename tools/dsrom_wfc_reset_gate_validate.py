#!/usr/bin/env python3
"""One pinned reset-gate campaign using the retained owner cases/checker.

No wall/AS/file/RAM caps. Run on EPYC2 through its unchanged admission script.
Every case has independent immutable logs/exit records. Routes are a separate
owner action only after all required functional terminals actually pass.
"""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CASES = {}
for seed, maxu, users, clat, pdly, plen in (
        (1,16,12,20,60,3),(2,40,37,5,10,1),(3,40,40,3,200,2),
        (4,64,50,40,30,4),(5,16,16,2,6,2),(6,33,33,8,0,5),
        (7,70,66,4,3,2),(8,100,100,1,2,1)):
    CASES[f'src_seed{seed}'] = ('icarus',dict(LOCKSTEP=0,SEED=seed,MAXU=maxu,USERS=users,CLAT=clat,PDLY=pdly,PLEN=plen))
for seed in (1,2,3):
    CASES[f'stg_seed{seed}'] = ('icarus',dict(SOURCE=0,SEED=seed,MAXU=seed*20,USERS=seed*15,RXWORDS=seed*3,XWORDS=seed*2+1))
CASES['eq866_s1'] = ('verilator',dict(SOURCE=1,LOCKSTEP=0,MAXU=866,USERS=866,SEED=11,CLAT=6,PDLY=40))
CASES['eq866_s0'] = ('verilator',dict(SOURCE=0,MAXU=866,USERS=866,SEED=13,NJOBS=20000,XWORDS=46,RXWORDS=41))
CASES['eq866_lat'] = ('verilator',dict(SOURCE=1,LOCKSTEP=0,MAXU=866,USERS=32,SEED=21,CLAT=12000,PDLY=600,PLEN=2,GEN=10,MAXCYC=100000000))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run_case(output, name, kind, params):
    out = output/name
    out.mkdir()
    if kind == 'icarus':
        cmd = ['iverilog','-g2012','-DWF_DUT=ot_rom_pkg_ctrl_wfc','-s','tb_wf_ctrl_equiv','-o',str(out/'case.vvp')]
        for k,v in params.items():cmd += ['-P',f'tb_wf_ctrl_equiv.{k}={v}']
        cmd += [str(ROOT/p) for p in ('rtl/test/dsrom_wavefront/tb_wf_ctrl_equiv_reset_admission.sv',
                                       'rtl/rom/wavefront/ot_rom_pkg_ctrl_wf.sv','rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc.sv')]
        (out/'build_command.json').write_text(json.dumps(cmd,indent=2)+'\n')
        with (out/'build.log').open('w') as log:rc = subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode
        if rc == 0:
            with (out/'run.log').open('w') as log:
                rc = subprocess.run(['vvp','-n',str(out/'case.vvp')],stdout=log,stderr=subprocess.STDOUT).returncode
    else:
        # This unchanged additive owner recipe compiles AND runs its checker.
        # It refuses existing output directories, so let it create the case.
        out.rmdir()
        cmd = ['bash',str(ROOT/'tools/dsrom_wfc_reset_reference_recipe.sh'),str(out)]
        cmd += [f'-G{k}={v}' for k,v in params.items()]
        with (output/f'{name}.supervisor.log').open('w') as log:
            rc = subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode
    text = (out/'run.log').read_text(errors='replace') if (out/'run.log').exists() else ''
    passed = rc == 0 and 'EQUIV PASS' in text and 'EQUIV FAIL' not in text
    record = dict(kind=kind,params=params,exit_code=rc,passed=passed,
                  terminal_lines=[line for line in text.splitlines() if line.startswith('EQUIV')])
    (out/'terminal.json').write_text(json.dumps(record,indent=2)+'\n')
    print(name, 'PASS' if passed else 'FAIL', flush=True)
    return name,record


def stage(output, prepared):
    name='stage9_w1'
    cmd = ['python3',str(ROOT/'tools/dsrom_wf_close.py'),'stage','--from',str(prepared),
           '--scratch',str(output/name),'--wave','1']
    env=dict(os.environ,OT_WF_JOBS='16')
    with (output/f'{name}.supervisor.log').open('w') as log:
        rc=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT).returncode
    out=output/name
    text=(out/'out_stage_w1.txt').read_text(errors='replace') if (out/'out_stage_w1.txt').exists() else ''
    report=json.loads((out/'stage_w1.json').read_text()) if (out/'stage_w1.json').exists() else {}
    passed=rc==0 and report.get('rc')==0 and 'PASS' in text and 'FAIL' not in text
    record=dict(kind='original_L20_stage',exit_code=rc,passed=passed,stage_report=report,
                terminal_lines=[line for line in text.splitlines() if 'PASS' in line or 'FAIL' in line])
    out.mkdir(exist_ok=True)
    (out/'terminal.json').write_text(json.dumps(record,indent=2)+'\n')
    print(name,'PASS' if passed else 'FAIL',flush=True)
    return name,record


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--stage-from',type=Path,required=True)
    args=ap.parse_args()
    output=args.output.resolve()
    output.mkdir(parents=True,exist_ok=False)
    pins={p:sha(ROOT/p) for p in ('rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc.sv',
                                 'rtl/rom/wavefront/ot_rom_pkg_ctrl_wf.sv',
                                 'rtl/test/dsrom_wavefront/tb_wf_ctrl_equiv_reset_admission.sv')}
    results={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(CASES)+1) as pool:
        futures=[pool.submit(run_case,output,n,*cfg) for n,cfg in CASES.items()]
        futures.append(pool.submit(stage,output,args.stage_from.resolve()))
        for future in concurrent.futures.as_completed(futures):
            name,record=future.result();results[name]=record
    unchanged=all(sha(ROOT/p)==v for p,v in pins.items())
    passed=unchanged and len(results)==len(CASES)+1 and all(r['passed'] for r in results.values())
    record=dict(verdict='PASS_FUNCTIONAL_ONLY' if passed else 'FAIL',source_sha256=pins,
                source_unchanged=unchanged,cases=results,physical_qualified=False)
    (output/'summary.json').write_text(json.dumps(record,indent=2)+'\n')
    (output/'exit_code').write_text('0\n' if passed else '1\n')
    print(record['verdict'],flush=True)
    return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())
