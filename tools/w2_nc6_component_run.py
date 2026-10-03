#!/usr/bin/env python3
"""One clean component compile/run after fresh local CPU admission; no caps.

No MemoryMax/SwapMax/AS/time/file/CPUquota. Affinity allocates two measured idle
CPUs; fixture has its own finite protocol watchdog. No automatic retry/fallback.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import time
ROOT=Path(__file__).resolve().parents[1]
TOOL=Path('/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator')
OUT=ROOT/'results/uarch/w2_nc6_component_20261003'
FILES=['rtl/experimental/w2_nc6_completion_20261003/ot_hdc_qwen_pc_exact_completion.sv',
       'rtl/test/w2_nc6_completion_20261003/tb.sv']

def hashfile(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def snap():
    data={}
    for line in Path('/proc/stat').read_text().splitlines():
        t=line.split()
        if t[0].startswith('cpu') and t[0]!='cpu':data[int(t[0][3:])]=list(map(int,t[1:9]))
    return data

def headroom():
    a=snap();time.sleep(1);b=snap();rows=[]
    for i in sorted(os.sched_getaffinity(0)):
        d=[y-x for x,y in zip(a[i],b[i])];rows.append(dict(cpu=i,idle_pct=100*(d[3]+d[4])/max(1,sum(d))))
    load=os.getloadavg();eligible=sorted((r for r in rows if r['idle_pct']>=50),key=lambda r:(-r['idle_pct'],r['cpu']))
    mem={t[0].rstrip(':'):int(t[1]) for l in Path('/proc/meminfo').read_text().splitlines() if len(t:=l.split())>=2 and t[1].isdigit()}
    return dict(load=list(load),eligible_cpu_count=len(rows),cpu_sample=rows,
        allocated_cpus=[r['cpu'] for r in eligible[:2]],
        available_memory_KiB=mem['MemAvailable'],disk_free_bytes=shutil.disk_usage('/tmp').free,
        admitted=len(eligible)>=2 and load[0]<len(rows),
        policy='2 >=50% idle CPUs, load1 below eligible CPU count; measured admission, not process limits')

def validate_runtime(text):
    expected=json.loads((OUT/'expected_cases.json').read_text())
    actual=re.findall(r'^CASE_PASS ([^ ]+) cycle=\d+$',text,re.M)
    return len(actual)==len(set(actual)) and set(actual)==set(expected) and 'COMPONENT_PASS' in text


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--preflight-only',action='store_true');a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    record=dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_pins={f:hashfile(ROOT/f) for f in FILES},preflight_only=a.preflight_only,
        process_caps='NONE; affinity allocation only',resource_estimate='Small NC6 component; no measured compile time/peak yet',
        compiler=str(TOOL),headroom=headroom(),compile_launched=False,runtime_launched=False)
    if TOOL.exists():
        record['compiler_version']=subprocess.check_output([str(TOOL),'--version'],text=True).strip()
        record['compiler_sha256']=hashfile(TOOL)
        record['compiler_bin_sha256']=hashfile(TOOL.parent/'verilator_bin')
    dirty=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)
    record['worktree_clean']=not bool(dirty)
    reasons=[]
    manifest=json.loads((OUT/'manifest.json').read_text())
    record['frozen_inputs_match']=all(hashfile(ROOT/r['path'])==r['sha256'] for r in manifest)
    if not record['frozen_inputs_match']:reasons.append('FROZEN_INPUT_MISMATCH')
    toolchain=json.loads((OUT/'toolchain.json').read_text())
    record['toolchain_matches_enrolled_hashes']=all(record.get(k)==v for k,v in toolchain.items())
    if not record['toolchain_matches_enrolled_hashes']:reasons.append('TOOLCHAIN_HASH_MISMATCH')
    if not record['headroom']['admitted']:reasons.append('NO_LOCAL_CPU_HEADROOM')
    if '5.050' not in record.get('compiler_version',''):reasons.append('PINNED_COMPILER_UNAVAILABLE')
    if dirty:reasons.append('WORKTREE_NOT_CLEAN')
    if a.preflight_only or reasons:
        record['verdict']='PREFLIGHT_ONLY' if not reasons else 'REFUSED_BEFORE_COMPILE'
        record['reasons']=reasons
    else:
        cpus=','.join(map(str,record['headroom']['allocated_cpus']))
        cmd=['taskset','-c',cpus,str(TOOL),'--binary','--timing','--top-module','tb','-j','2','-Wno-fatal','--Mdir',str(a.out/'obj')]+[str(ROOT/f) for f in FILES]
        record['compile_command']=cmd;record['compile_launched']=True;t=time.monotonic()
        with (a.out/'compile.log').open('w') as log:r=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        record['compile_seconds']=time.monotonic()-t;record['compile_returncode']=r.returncode
        record['verdict']='COMPILE_FAIL'
        if r.returncode==0:
            binary=a.out/'obj/Vtb';record['binary_sha256']=hashfile(binary);record['runtime_launched']=True
            with (a.out/'runtime.log').open('w') as log:r=subprocess.run(['taskset','-c',cpus,str(binary)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            record['runtime_returncode']=r.returncode
            record['verdict']='PASS_COMPONENT_FUNCTIONAL_ONLY' if r.returncode==0 and validate_runtime((a.out/'runtime.log').read_text()) else 'RUNTIME_FAIL'
    (a.out/'record.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
    print(json.dumps(record,indent=2,sort_keys=True))
    return 0 if a.preflight_only or record['verdict']=='PASS_COMPONENT_FUNCTIONAL_ONLY' else 1
if __name__=='__main__':raise SystemExit(main())
