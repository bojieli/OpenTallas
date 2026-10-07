#!/usr/bin/env python3
"""Minimum two-lane protocol gate at actual 100/400-cycle channels from a pinned source archive."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import subprocess
ROOT=Path(__file__).resolve().parents[1]
FILES=['rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_pipeline.sv',
       'rtl/dsrom_sys/s81_ph/coll/ot_s81ph_skid2.sv','rtl/dsrom_sys/s81_ph/coll/ot_s81ph_ckbuf.sv',
       'rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep.sv','rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx_pipeline.sv',
       'rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv','rtl/dsrom_sys/s81_ph/ot_s81ph_rfifo.sv',
       'rtl/link/ot_link_crc32.sv',
       'physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v']

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source',required=True,type=Path)
    ap.add_argument('--out',required=True,type=Path);ap.add_argument('--verilator',default='verilator')
    a=ap.parse_args();src=a.source.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    pin=(src/'SOURCE_COMMIT').read_text().strip()
    if len(pin)!=40 or any(c not in '0123456789abcdef' for c in pin): raise ValueError('Missing full source pin')
    bench=ROOT/'rtl/dsrom_sys/s81_ph/test/tb_s81ph_gbx_pipeline_pair.sv'
    rec={'source_pin':pin,'source_sha256':{p:hashlib.sha256((src/p).read_bytes()).hexdigest() for p in FILES},
         'bench_sha256':hashlib.sha256(bench.read_bytes()).hexdigest(),'runs':{}}
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    for ch in [100,400]:
        label='channel_'+str(ch);build=out/(label+'_build')
        cmd=[a.verilator,'--binary','--timing','-Wno-fatal','--top-module','tb_s81ph_gbx_pipeline_pair',
             '-GCH='+str(ch),'-GBOARD='+str(int(ch==400)),'--Mdir',str(build),str(bench)]+[str(src/p) for p in FILES]
        with (out/(label+'_build.log')).open('w') as fd:
            rc=subprocess.run(cmd,cwd=src,stdout=fd,stderr=subprocess.STDOUT).returncode
        if rc: raise RuntimeError(f'{label} build failed {rc}')
        with (out/(label+'.log')).open('w') as fd:
            rc=subprocess.run([str(build/'Vtb_s81ph_gbx_pipeline_pair')],cwd=out,stdout=fd,stderr=subprocess.STDOUT).returncode
        log=(out/(label+'.log')).read_text()
        rec['runs'][label]={'returncode':rc,'pass':rc==0 and 'PAIR PASS' in log and 'timeouts=0/0' in log,'output':log}
    rec['pass']=all(r['pass'] for r in rec['runs'].values())
    (out/'summary.json').write_text(json.dumps(rec,indent=2)+'\n')
    if not rec['pass']: raise SystemExit(1)

if __name__=='__main__':main()
