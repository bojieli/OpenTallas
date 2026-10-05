#!/usr/bin/env python3
"""One explicit source-pinned gate arm; no retry or automatic fallback."""
import argparse,hashlib,json,os,resource,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/rtl/dsrom_window_owner_tag_gate_20261003'

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--arm',choices=['original','owner-safe'],required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('fresh output directory required; preserve first attempt')
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip():raise ValueError('clean pinned source required')
    for pin in json.loads((BASE/'input_pins.json').read_text()):
        if hashlib.sha256((BASE/pin['archive']).read_bytes()).hexdigest()!=pin['sha256']:raise ValueError('source pin mismatch')
    a.out.mkdir(parents=True)
    (a.out/'model.json').write_bytes((BASE/'model.json').read_bytes())
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    versions={name:subprocess.run([name,'-V'],capture_output=True,text=True).stdout for name in ['iverilog','vvp']}
    mem=Path('/proc/meminfo').read_text();disk=os.statvfs(a.out)
    if int(next(x.split()[1] for x in mem.splitlines() if x.startswith('MemAvailable:')))*1024<2**30:raise ValueError('measured host RAM admission refused')
    if disk.f_bavail*disk.f_frsize<2**30:raise ValueError('measured disk reserve refused')
    receipt=dict(source_commit=head,arm=a.arm,status='STARTED',host=dict(meminfo=mem,available_disk_bytes=disk.f_bavail*disk.f_frsize),versions=versions,limits=dict(FSIZE='unlimited',CPU_time='unlimited',wall_limit=None,extra_large_job=False),HDL_execution=True,physical_credit=False,fulltoken_credit=False)
    def preserve():(a.out/'record.json').write_text(json.dumps(receipt,indent=2)+'\n')
    def unlimited():
        resource.setrlimit(resource.RLIMIT_FSIZE,(resource.RLIM_INFINITY,resource.RLIM_INFINITY));resource.setrlimit(resource.RLIMIT_CPU,(resource.RLIM_INFINITY,resource.RLIM_INFINITY))
    src=[BASE/'inputs'/('ot_chip_v41x_'+x+'.sv') for x in ['window_stage4','window_row_codec','kv_reqmux','kv_rope_reqmux']]
    pf=BASE/'inputs/ot_chip_v41x_window_kv_prefetch.sv'
    opts=[]
    if a.arm=='owner-safe':
        pf=BASE/'owner_safe/ot_chip_v41x_window_kv_prefetch_owner_safe.sv';opts=['-DOWNER_SAFE_BUILD','-Ptb_window_owner_tag.OWNER_SAFE=1']
    files=src+[pf,BASE/'tb_window_owner_tag.sv']
    receipt['file_sha256']={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in files};preserve()
    try:
        exe=a.out/'gate.vvp';cmd=['iverilog','-g2012','-s','tb_window_owner_tag',*opts,'-o',str(exe),*map(str,files)]
        receipt['compile_command']=cmd
        with (a.out/'compile.log').open('w') as log:
            r=subprocess.run(['/usr/bin/time','-v',*cmd],stdout=log,stderr=subprocess.STDOUT,preexec_fn=unlimited)
        receipt['build_exit']=r.returncode;preserve()
        if r.returncode:receipt['status']='FAIL_BUILD_NO_QUALIFICATION';return
        with (a.out/'simulate.log').open('w') as log:
            r=subprocess.run(['/usr/bin/time','-v','vvp',str(exe)],stdout=log,stderr=subprocess.STDOUT,preexec_fn=unlimited)
        receipt['sim_exit']=r.returncode;text=(a.out/'simulate.log').read_text()
        marker='WINDOW_OWNER_NEGATIVE_CONFIRMED' if a.arm=='original' else 'WINDOW_OWNER_SAFE_PASS'
        lines=[x for x in text.splitlines() if x.startswith(marker)]
        if r.returncode or len(lines)!=1 or 'OTHER_FAULT' in text:receipt['status']='FAIL_UNEXPECTED_NO_QUALIFICATION'
        else:receipt['status']='CONFIRMED_ORIGINAL_DUT_OWNER_REJECTION' if a.arm=='original' else 'PASS_BOUNDED_WINDOW_TAG_GATE_ONLY';receipt['completion']=lines[0]
        receipt['binary_sha256']=hashlib.sha256(exe.read_bytes()).hexdigest()
    except BaseException as e:
        receipt['status']='FAIL_INFRASTRUCTURE';receipt['diagnosis']=repr(e);raise
    finally:
        receipt['artifact_sha256']={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in a.out.iterdir() if x.is_file() and x.name!='record.json'};preserve()

if __name__=='__main__':main()
