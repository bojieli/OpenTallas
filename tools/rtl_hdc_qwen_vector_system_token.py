#!/usr/bin/env python3
"""Source-pinned G4/SW16 Qwen token through the physical vector KV system."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import rtl_hdc_spec_token_campaign as BASE

KV=[ROOT/p for p in (
    'rtl/hdc/kv/ot_hdc_kv_walk.sv','rtl/hdc/kv/ot_hdc_kv_stream.sv',
    'rtl/hdc/kv/ot_hdc_qwen_kv_tail_read_mux.sv',
    'rtl/hdc/kv/ot_hdc_qwen_kv_tail_bank_port.sv',
    'rtl/hdc/kv/ot_hdc_qwen_kv_tail_group_port.sv',
    'rtl/hdc/kv/ot_hdc_qwen_hbm_sector_bridge.sv',
    'rtl/hdc/kv/ot_hdc_qwen_kv_phys_arbiter.sv',
    'rtl/hdc/kv/ot_hdc_qwen_kv_hbm_boot.sv',
    'rtl/hdc/kv/ot_hdc_qwen_kv_system.sv')]
TB=ROOT/'rtl/test/tb_hdc_core_qwen_system.sv'
INPUTS=[*BASE.HDC,*BASE.PIPES,*BASE.BRIDGE_RTL,*KV,TB,BASE.HARNESS,BASE.ISA_SVH,
        ROOT/'tools/hdc_program.py',ROOT/'tools/hdc_golden.py',Path(__file__)]

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,default=ROOT/'results/rtl/hdc_qwen_vector_system_token_g4sw16.json')
    args=ap.parse_args()
    env=dict(os.environ,HDC_GROUPS='4',HDC_SU_WIDTH='16',HDC_KV_FMT='fp8')
    rec={'schema':'opentallas.qwen-vector-system-token.v1',
         'configuration':{'groups':4,'su_width':16,'context':64,'physical_hbm_bytes':32},
         'claim_boundary':'functional one-token simulation through finite vector write FIFO, '
                          'banked K tail, streamer prefetch window and serialized 32-byte HBM; '
                          'the HBM test model has one-cycle reads and no bandwidth/refresh calibration',
         'input_sha256':{str(p.relative_to(ROOT)):sha(p) for p in INPUTS}}
    with tempfile.TemporaryDirectory(prefix='qwen_vec_system_token_') as td:
        td=Path(td); img=td/'img'; obj=td/'obj'
        gen=subprocess.run([sys.executable,str(ROOT/'tools/hdc_program.py'),'--out',str(img),
                            '--context','64'],cwd=ROOT,env=env,capture_output=True,text=True)
        if gen.returncode:
            rec.update(status='fail',phase='image',stderr=gen.stderr[-4000:])
        else:
            cmd=['verilator','--cc','--exe','--build','-O2','-Wno-fatal','-Wno-WIDTH',
                 '-Wno-UNUSED','-Wno-BLKSEQ','-Wno-VARHIDDEN','--unroll-count','65536',
                 '--top-module','tb_hdc_core','-GG=4','-GSW=16','-GKV_BRIDGE=0',
                 '-Mdir',str(obj),f'-I{BASE.ISA_SVH.parent}',
                 *map(str,BASE.HDC+BASE.PIPES+BASE.BRIDGE_RTL+KV),str(TB),str(BASE.HARNESS),
                 '-CFLAGS','-O1']
            build=subprocess.run(cmd,cwd=ROOT,env=dict(os.environ,MAKEFLAGS='-j8'),
                                 capture_output=True,text=True)
            if build.returncode:
                rec.update(status='fail',phase='build',returncode=build.returncode,
                           stderr=build.stderr[-8000:])
            else:
                sim=subprocess.run([str(obj/'Vtb_hdc_core'),f'+DIR={img}',
                                    *(img/'run.args').read_text().split()],cwd=ROOT,
                                   capture_output=True,text=True)
                output=sim.stdout
                m=BASE.SINGLE.search(output)
                traffic=re.search(r'KV_SYSTEM fault=(\d+) drained=(\d+) hbm_reads=(\d+) '
                                  r'hbm_writes=(\d+) wait_cycles=(\d+)',output)
                if m:
                    names=['token','position','next_token','expected_token','cycles','core_fault',
                           'logit_mismatches','vm_mismatches','kv_mismatches']
                    rec.update(dict(zip(names,map(int,m.groups()))))
                if traffic:
                    rec['kv_system']=dict(zip(('fault','drained','hbm_reads','hbm_writes','wait_cycles'),
                                              map(int,traffic.groups())))
                rec.update(status='pass' if sim.returncode==0 and 'PASS' in output and m and
                           traffic and rec['next_token']==rec['expected_token'] else 'fail',
                           phase='simulation',returncode=sim.returncode,
                           stdout=output[-10000:],stderr=sim.stderr[-4000:])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(rec,indent=2)+'\n')
    print(args.output,rec['status'],rec.get('phase'))
    return 0 if rec['status']=='pass' else 1

if __name__=='__main__': raise SystemExit(main())
