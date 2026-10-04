#!/usr/bin/env python3
"""Build the existing selected attention adapter/cut only; no runtime or core.

Submit via the owner's admit.sh with a peak estimate, not a process limit.
The generated adapter preserves the full source buffers; the endpoint retains
all 64 H16/TD32 attention tiles and the original arithmetic hierarchy.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = 'rtl/w17_runtime/hdc/v41x/ot_hdc_v41x_att_adapt.sv'
ENGINE = ['rtl/hdc/v41x/' + n + '.sv' for n in
          ('ot_hdc_v41x_attn_tile', 'ot_hdc_v41x_attn', 'ot_hdc_v41x_attn_staging')]
ENGINE += ['physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v',
           'rtl/hdc/ot_hdc_fastfp.sv']
HIER = 'results/rtl/v41_attention_elaboration_archive/tools/v41_attention_hierarchy.vlt'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--source-commit', required=True)
    p.add_argument('--jobs', type=int, default=2)
    p.add_argument('--verilator', required=True)
    a = p.parse_args()
    if a.jobs < 1:
        p.error('positive worker allocation required')
    a.out = a.out.resolve()
    a.out.mkdir(parents=True, exist_ok=False)
    paths = [ADAPTER, HIER, *ENGINE]
    paths += [str(f.relative_to(ROOT)) for f in (ROOT/'tools/runtime/dsrom').glob('*.hpp')]
    paths += ['tools/runtime/dsrom/s81_minimum_me_attention.cpp', str(Path(__file__).relative_to(ROOT))]
    record = dict(source_commit=a.source_commit, supervisor_pid=os.getpid(),
                  source_pins={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in paths},
                  tool_version=subprocess.check_output([a.verilator,'--version'],text=True).strip(),
                  tool_path=str(Path(a.verilator).resolve()),
                  compiler_version=subprocess.check_output(['g++','--version'],text=True).splitlines()[0],
                  worker_allocation=a.jobs, stages=[],
                  scope='Native full-shape adapter and attention cut libraries only; no runtime/physical/token claim')
    if 'Verilator 5.050' not in record['tool_version']:
        raise RuntimeError('selected Verilator version mismatch')
    vroot=Path(a.verilator).resolve().parents[1]/'share/verilator/include'
    adapter=a.out/'adapter'; engine=a.out/'engine'
    common=[a.verilator,'--cc','--build','-j',str(a.jobs),'-Wno-fatal',
            '--output-split','20000','--output-split-cfuncs','2000',
            '-CFLAGS','-O0','-MAKEFLAGS','OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0']
    commands=[('adapter',common+['--top-module','ot_hdc_v41x_att_adapt','--prefix','VDsromAttention',
        '--Mdir',str(adapter),'-DV41_ATT_CUT',
        *['-G'+k+'='+str(v) for k,v in dict(W=16,G=4,IL=8,AW=30,NW=21,MP=1,H=16,D=512,TD=32,NL=4,TROWS=640,NHMAX=16,PACKED_KV=1).items()],
        str(ROOT/ADAPTER)]),
      ('provider',['g++','-std=c++17','-O0','-pthread',
        '-I'+str(ROOT/'tools/runtime/dsrom'),'-I'+str(ROOT/'tools/native'),
        '-I'+str(ROOT/'rtl/test/v41_runtime'),'-I'+str(adapter),
        '-isystem',str(vroot),'-isystem',str(vroot/'vltstd'),
        '-c',str(ROOT/'tools/runtime/dsrom/s81_minimum_me_attention.cpp'),
        '-o',str(a.out/'s81_minimum_me_attention.o')]),
      ('engine',common+['--top-module','ot_hdc_v41x_attn','--prefix','VDsromAttEngine',
        '--Mdir',str(engine),'--hierarchical','--unroll-count','1','--unroll-limit','131072',
        *['-G'+k+'='+str(v) for k,v in dict(H=16,D=512,TD=32,NL=4,TROWS=640,PWORDS=1).items()],
        str(ROOT/HIER),*[str(ROOT/s) for s in ENGINE]])]
    code=1
    try:
        for name,cmd in commands:
            start=time.monotonic()
            with (a.out/(name+'.log')).open('x') as log:
                proc=subprocess.Popen(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
                record['active_stage']=name;record['active_pid']=proc.pid
                record['command']=cmd
                (a.out/'progress.json').write_text(json.dumps(record,indent=2)+'\n')
                code=proc.wait()
            record['stages'].append(dict(name=name,exit=code,seconds=time.monotonic()-start,command=cmd))
            if code:
                break
        if not code:
            artifacts=[adapter/'VDsromAttention.h',adapter/'VDsromAttention__ALL.a',
                       engine/'VDsromAttEngine.h',engine/'VDsromAttEngine__ALL.a',a.out/'s81_minimum_me_attention.o']
            record['artifacts']={str(f):dict(bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for f in artifacts}
    finally:
        record['exit']=code;record['verdict']='PASS_LIBRARIES_ONLY' if code==0 else 'FAIL_PRESERVED'
        (a.out/'terminal.json').write_text(json.dumps(record,indent=2)+'\n')
    return code


if __name__=='__main__':
    raise SystemExit(main())
