#!/usr/bin/env python3
"""Run full-width original/candidate/default equivalence and a wrong-head negative control."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ['rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx.sv',
           'rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx_pipeline.sv',
           'rtl/dsrom_sys/s81_ph/test/tb_s81ph_gbx_pipeline.sv']

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--verilator',default='verilator'); a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    record={'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},'runs':{}}
    for name in ['exact','wrong_shift_negative']:
        paths=[str(ROOT/p) for p in SOURCES]
        if name!='exact':
            mutant=a.out/'wrong_head.sv'
            text=(ROOT/SOURCES[1]).read_text()
            needle = "ins_lo << {ins_upper, 4'b0000}"
            assert text.count(needle)==1
            mutant.write_text(text.replace(needle, "ins_lo << {ins_upper, 3'b000}"))
            paths[1]=str(mutant.resolve())
        build=a.out/(name+'_build')
        cmd=[a.verilator,'--binary','--timing','-Wno-fatal','--top-module','tb_s81ph_gbx_pipeline','--Mdir',str(build.resolve())]+paths
        with (a.out/(name+'_build.log')).open('w') as log:
            rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT).returncode
        if rc: raise RuntimeError(f'{name} failed to build: {rc}')
        with (a.out/(name+'.log')).open('w') as log:
            rc=subprocess.run([str((build/'Vtb_s81ph_gbx_pipeline').resolve())],stdout=log,stderr=subprocess.STDOUT,cwd=a.out).returncode
        log=(a.out/(name+'.log')).read_text()
        passed=(rc==0 and 'PASS cycles=24000' in log) if name=='exact' else (rc!=0 and 'PIPE mismatch cycle' in log)
        record['runs'][name]={'returncode':rc,'gate_pass':passed,'output':log}
    record['pass']=all(r['gate_pass'] for r in record['runs'].values())
    (a.out/'summary.json').write_text(json.dumps(record,indent=2)+'\n')
    if not record['pass']: raise SystemExit(1)

if __name__=='__main__': main()
