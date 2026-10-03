#!/usr/bin/env python3
"""Enroll actual primary/secondary/codec/corrector with the fullNC6 fixture.
One new output per invocation; preserve every compile/runtime failure.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import time
from w2_fullnc6_fixture import selected_primary,selected_secondary

ROOT=Path(__file__).resolve().parents[1]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def cpu_sample():
    rows={}
    for line in Path('/proc/stat').read_text().splitlines():
        fields=line.split()
        if fields and fields[0].startswith('cpu') and fields[0][3:].isdigit():
            ticks=[int(x) for x in fields[1:9]]
            rows[int(fields[0][3:])]=(sum(ticks),ticks[3])
    return rows

def idle_cpu_equivalents(before,after,allowed):
    available=0.0
    for cpu in allowed:
        if cpu not in before or cpu not in after:continue
        total=after[cpu][0]-before[cpu][0];idle=after[cpu][1]-before[cpu][1]
        if total>0:available+=max(0.0,min(1.0,idle/total))
    return available

def choose_jobs(available,requested=None):
    free=math.floor(available)
    if free<1:raise ValueError('NO_LOCAL_CPU_HEADROOM')
    jobs=min(32,free) if requested is None else requested
    if jobs<1 or jobs>free:raise ValueError('REQUESTED_JOBS_EXCEED_MEASURED_CPU_HEADROOM')
    return jobs

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--primary-root',type=Path,default=Path('/home/ubuntu/w2-pc-exact-completion-model-20261003'))
    p.add_argument('--corrector-root',type=Path,default=Path('/tmp/Hubble-W2-corrector-rescue-20261003'))
    p.add_argument('--corrector-sha256',help='require exact admitted split-helper source hash')
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--simulator',choices=['iverilog','verilator'],default='iverilog')
    p.add_argument('--jobs',type=int,help='compile workers; default up to32 from fresh measured idle CPUs')
    p.add_argument('--output-split',type=int,default=10000,help='generated C++ statements per file')
    p.add_argument('--output-split-cfuncs',type=int,default=1000,help='generated model statements per function')
    p.add_argument('--reset-quarantine',action='store_true',help='enroll matching opt-in reset-quarantine successor sources')
    p.add_argument('--reference-negative',choices=['omit','drop','drop_debt','consume'],
                   help='select one expected-FAIL reset receipt mutant in the existing fixture')
    p.add_argument('--fault-matrix',action='store_true')
    p.add_argument('--full-double-pairs',action='store_true')
    a=p.parse_args()
    if a.full_double_pairs and not a.fault_matrix:p.error('--full-double-pairs requires --fault-matrix')
    # Run fixed fixture source, not evolving preparation changes.
    if subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True).strip():
        raise SystemExit('fixture tracked source is dirty')
    a.out.mkdir();inputs=a.out/'inputs';inputs.mkdir()
    files=[selected_primary(a.primary_root,a.reset_quarantine),
           selected_secondary(a.primary_root,a.reset_quarantine),
           a.primary_root/'rtl/experimental/w2_nc6_protection_20261003/ot_w2_sealed_secded72.sv',
           a.corrector_root/'rtl/experimental/w2_nc6_correction_control_split_20261003/ot_w2_nc6_correction_control.sv',
           ROOT/'rtl/test/w2_fullnc6_functional_20261003/tb.sv']
    if a.corrector_sha256 and sha(files[3]) != a.corrector_sha256:
        raise SystemExit('split-helper source pin mismatch; no compile')
    pins={}
    for f in files:
        data=f.read_bytes();(inputs/f.name).write_bytes(data)
        pins[str(f)]=hashlib.sha256(data).hexdigest()
    record=dict(fixture_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_pins=pins,pid=os.getpid(),utc_start=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        capacity=dict(mem_available=next(x for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')),
                      disk_free_bytes=shutil.disk_usage(a.out).free,affinity=sorted(os.sched_getaffinity(0)),load=os.getloadavg()),
        fault_matrix_selected=a.fault_matrix,full_double_pairs_selected=a.full_double_pairs,
        physical_or_fulltoken_admission=False,reset_quarantine_selected=a.reset_quarantine,reference_negative=a.reference_negative,
        reference_negative_expected='FAIL_RUNTIME' if a.reference_negative else None,status='COMPILING')
    def save(): (a.out/'record.json').write_text(json.dumps(record,indent=2)+'\n')
    if a.simulator=='verilator':
        version=subprocess.check_output(['verilator','--version'],text=True).strip()
        if not version.startswith('Verilator 5.050 '):
            raise SystemExit('exact Verilator5.050 required')
        record['simulator_version']=version
        before=cpu_sample();time.sleep(0.25);after=cpu_sample()
        available=idle_cpu_equivalents(before,after,os.sched_getaffinity(0))
        record['capacity']['measured_idle_cpu_equivalents']=available
        record['capacity']['cpu_sample_seconds']=0.25
        try:jobs=choose_jobs(available,a.jobs)
        except ValueError as error:
            record.update(status='REFUSED_BEFORE_COMPILE',reason=str(error));save()
            raise SystemExit(str(error))
        record['compile_workers']=jobs
        cmd=['verilator','--binary','--timing','--top-module','tb_w2_fullnc6',
             '-Wno-fatal','-j',str(jobs),'--output-split',str(a.output_split),
             '--output-split-cfuncs',str(a.output_split_cfuncs),
             '--Mdir',str(a.out/'obj'),'-o',str(a.out/'gate.bin'),
             *[str(inputs/f.name) for f in files]]
    else:
        cmd=['iverilog','-g2012','-s','tb_w2_fullnc6','-o',str(a.out/'gate.bin'),*[str(inputs/f.name) for f in files]]
    record['simulator']=a.simulator
    record['compile_command']=cmd;save();print('COMPILE',os.getpid(),a.out,flush=True)
    t=time.monotonic()
    with (a.out/'compile.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
    record.update(compile_rc=r.returncode,compile_seconds=time.monotonic()-t);save()
    if r.returncode==0:
        record['binary_sha256']=sha(a.out/'gate.bin');record['status']='RUNNING';save()
        cmd=([str(a.out/'gate.bin')] if a.simulator=='verilator' else ['vvp',str(a.out/'gate.bin')])
        if a.fault_matrix:cmd.append('+fault_matrix')
        if a.full_double_pairs:cmd.append('+full_double_pairs')
        if a.reference_negative:cmd.append('+oracle_reset_'+a.reference_negative)
        record['runtime_command']=cmd;print('RUN',flush=True);t=time.monotonic()
        with (a.out/'runtime.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
        text=(a.out/'runtime.log').read_text()
        record.update(runtime_rc=r.returncode,runtime_seconds=time.monotonic()-t,
                      case_pass_lines=[x for x in text.splitlines() if x.startswith('CASE_PASS')],
                      measurement_lines=[x for x in text.splitlines() if x.startswith('MEASURE')])
        record['status']='PASS_FUNCTIONAL' if not a.reference_negative and r.returncode==0 and 'COMPONENT_PASS' in text else 'FAIL_RUNTIME'
        if a.reference_negative:
            expected_message={'omit':'rejected stale return retired reset-orphan debt',
                              'drop':'reset orphan receipt dropped without provider disposal',
                              'drop_debt':'external accepted receipt conservation',
                              'consume':'client terminal consumed quarantined reset orphan'}[a.reference_negative]
            record['reference_negative_expected_message']=expected_message
            record['reference_negative_observed_failure']=r.returncode!=0 and expected_message in text and 'COMPONENT_PASS' not in text
    else:record['status']='FAIL_COMPILE'
    record['source_pins_post']={str(f):sha(f) for f in files};save();print(record['status'],flush=True)
    return 0 if record['status']=='PASS_FUNCTIONAL' else 1

if __name__=='__main__':raise SystemExit(main())
