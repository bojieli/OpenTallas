"""EPYC2-only admitted exactness gate for the DS-KV descriptor guards with real SRAM primitives.

Source commit must describe the committed parent vehicle; hashes pin candidate edits.
Run on climbing-locust. --peak-gb must come from the build inventory/measurement.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TOP = 'tb_hbm_accel_dskv_descriptor_guard'
SOURCES = [
    'rtl/common/ot_secded.sv',
    'rtl/hbm_accel/service/ot_hbm_accel_dskv_shadow_sram.sv',
    'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',
    'rtl/hbm_accel/service/ot_hbm_accel_dskv_wb_sram.sv',
    'rtl/test/hbm_accel/tb_hbm_accel_dskv_descriptor_guard.sv',
]
PINS = SOURCES + ['rtl/common/ot_secded_cols.svh', 'tools/hbm_accel_dskv_descriptor_guard_gate.py']


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--source-commit', required=True)
    ap.add_argument('--peak-gb', type=float, required=True)
    ap.add_argument('--jobs', type=int, default=2)
    ap.add_argument('--verilator', default=os.environ.get('VERILATOR', str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')))
    a = ap.parse_args()
    if os.uname().nodename != 'climbing-locust':
        raise SystemExit('owner requires remote EPYC2 execution; local builds are prohibited')
    if a.out.exists() or a.work.exists():
        raise SystemExit('fresh output and build directory required; preserve prior failure evidence')
    if a.peak_gb <= 0 or a.jobs <= 0:
        raise SystemExit('positive measured reservation and jobs required')
    pins = {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in PINS}
    a.work.mkdir(parents=True)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ['/srv/opentallas-scratch/admit.sh', str(a.peak_gb), '--', '/usr/bin/time', '-v',
           a.verilator, '--binary', '--timing', '-Wno-fatal', '-j', str(a.jobs), '-O2',
           '--top-module', TOP, '--Mdir', str(a.work/'obj'), '-I'+str(ROOT/'rtl/common')]
    cmd += [str(ROOT/p) for p in SOURCES]
    rec = dict(schema='opentallas.hbm_accel.dskv_descriptor_guard_gate.v1', source_commit=a.source_commit,
               input_sha256=pins, host=os.uname().nodename, admission_peak_gb=a.peak_gb,
               admission_guard='/srv/opentallas-scratch/admit.sh', clock_ns=.833,
               sources=SOURCES, cases=[], verdict='FAIL')
    for mut in (0,1):
        variant_cmd=list(cmd)
        variant_cmd[variant_cmd.index('--Mdir')+1]=str(a.work/f'obj{mut}')
        variant_cmd.append(f'-GMUT={mut}')
        with (a.work/f'build_mut{mut}.log').open('w') as log:
            build=subprocess.run(variant_cmd,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT)
        build_text=(a.work/f'build_mut{mut}.log').read_text()
        rss=re.search(r'Maximum resident set size \(kbytes\): (\d+)',build_text)
        row=dict(mut=mut,build_returncode=build.returncode,
                 build_max_rss_kib=int(rss[1]) if rss else None,verdict='MISSING',metrics={})
        if build.returncode==0:
            run=subprocess.run([str(a.work/f'obj{mut}'/('V'+TOP))],
                               stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            (a.work/f'case_mut{mut}.log').write_text(run.stdout)
            match=re.search(r'^GUARD_METRICS (.*)$',run.stdout,re.M)
            row['metrics']=dict((k,int(v)) for k,v in re.findall(r'(\w+)=(-?\d+)',match[1])) if match else {}
            verdict=re.search(r'^GUARD_VERDICT (PASS|FAIL)$',run.stdout,re.M)
            row.update(returncode=run.returncode,verdict=verdict[1] if verdict else 'MISSING')
        rec['cases'].append(row)
    good,negative=rec['cases']
    m=good['metrics']
    coverage=(m.get('cases')==20 and m.get('positive_posts')==3 and
              m.get('positive_writes')==20 and m.get('positive_reads')==3 and m.get('nonowner_drop')==1 and m.get('bad')==0)
    rec['verdict']='PASS' if (good.get('returncode')==0 and good['verdict']=='PASS' and coverage
        and negative.get('returncode',0)!=0 and negative['verdict']=='FAIL' and negative['metrics'].get('bad',0)>0) else 'FAIL'
    rec['input_unchanged'] = pins == {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in PINS}
    if not rec['input_unchanged']:
        rec['verdict']='FAIL'
    with a.out.open('x') as out:
        json.dump(rec,out,indent=2); out.write('\n')
    print(json.dumps(rec,indent=2))
    raise SystemExit(0 if rec['verdict']=='PASS' else 1)

if __name__ == '__main__':
    main()
