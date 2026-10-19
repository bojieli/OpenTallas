#!/usr/bin/env python3
"""Run in a fleet scratch copy with Verilator 5.050, never on localhost."""
import argparse, hashlib, json, os, re, subprocess
from pathlib import Path
from fault_bench import fixture, generate

p=argparse.ArgumentParser(); p.add_argument('--plan'); p.add_argument('--rtl',default='rtl/qwen_sys/split_20261014/qkd_astk_phys.sv'); p.add_argument('--source-commit',required=True); a=p.parse_args()
version=subprocess.check_output(['verilator','--version'],text=True).strip()
if '5.050' not in version: raise SystemExit('requires fleet Verilator 5.050: '+version)
rtl=Path(a.rtl).resolve(); plan=json.loads(Path(a.plan).read_text()) if a.plan else fixture()
root=Path('bench_output'); root.mkdir(exist_ok=True)
(root/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
summary=dict(source_commit=a.source_commit,rtl_sha256=hashlib.sha256(rtl.read_bytes()).hexdigest(),verilator=version,qualification='abstract topology admission only; fixed transport delays do NOT establish physical CDC signoff',tests={})
for mutant in ('none','missingfold','duplicate_wrongbranch'):
    out=root/mutant; meta=generate(plan,out,mutant)
    cmd=['verilator','--binary','--timing','--top-module','tb','-Wno-fatal','--build-jobs','2','--Mdir','obj',str(rtl),'tb.sv']
    build=subprocess.run(cmd,cwd=out,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    (out/'build.log').write_text(build.stdout)
    if build.returncode: raise SystemExit('BUILD_FAILED '+mutant+'\n'+build.stdout[-3000:])
    run=subprocess.run(['./obj/Vtb'],cwd=out,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    (out/'run.log').write_text(run.stdout)
    passed=run.returncode==0 and 'FAULT_PLANE_PASS' in run.stdout if mutant=='none' else run.returncode!=0 and 'FAULT_MISMATCH' in run.stdout and 'case=1 ' in run.stdout
    summary['tests'][mutant]=dict(pass_=passed,exit_code=run.returncode,manifest=meta,log=run.stdout)
    print(mutant+': '+run.stdout,flush=True)
    if not passed: raise SystemExit('BAD_VERDICT '+mutant)
# Refuse quiet window below the source-to-sink latency bound.
bad=dict(plan,retirement_quiet_cycles=0)
try: generate(bad,root/'bad_quiet')
except ValueError as e:
    if 'quiet window' not in str(e): raise
    summary['quiet_refusal']=str(e)
else: raise SystemExit('short retirement quiet window accepted')
(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print('FLEET_FAULT_BENCH_PASS '+str(root.resolve()),flush=True)
