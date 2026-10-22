#!/usr/bin/env python3
"""Run on an admitted fleet host; create real compiler views and cycle proof."""
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools/mem_compiler'))
import asap7
import sram_gen
NAME='ot_sram_1r1w_128x64_m1_p192'
asap7.METAL['pin_pitch_um']=0.192
sheet=sram_gen.compile_macro(sram_gen.SramSpec(NAME,128,64,mux=1,ports='1r1w'), ROOT/'physical/asap7_memory_macros')
macro=ROOT/'physical/asap7_memory_macros'/NAME
w=sheet['area']['macro_width_um'];h=sheet['area']['macro_height_um']
faces={'W':[],'E':[]}
for name,block in re.findall(r'  PIN (\S+)\n(.*?)  END \1',(macro/(NAME+'.lef')).read_text(),re.S):
    if 'USE POWER' in block or 'USE GROUND' in block:continue
    r=re.search(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',block)
    x0,y0,x1,y1=map(float,r.groups());faces['W' if x0<w/2 else 'E'].append((y0+y1)/2)
audit={}
for face,ys in faces.items():
    ys=sorted(ys);pitch=min(b-a for a,b in zip(ys,ys[1:]))
    assert len(ys)/h<=6 and pitch>=1/6-1e-9
    audit[face]={'pins':len(ys),'pins_per_um':len(ys)/h,'minimum_pin_pitch_um':pitch}
record={'host':socket.gethostname(),'source_base_commit':os.environ.get('SOURCE_BASE_COMMIT'),
        'compiler_source_commit':os.environ.get('COMPILER_SOURCE_COMMIT'),
        'macro':NAME,'area':sheet['area'],'pin_pitch_um':0.192,'faces':audit,
        'timing':sheet['timing'],'views':sheet['views'],'claim_boundary':sheet['claim_boundary'],
        'source_sha256':{},'runs':[]}
rtl=ROOT/'rtl/qwen_sys/host_20261013/qkd_host_guard_fifo.sv'
sources=[macro/(NAME+'.v'),rtl,HERE/'qkd_host_guard_fifo_ref.sv',HERE/'tb_guard_fifo_sram.sv']
for p in sources:record['source_sha256'][str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
run=HERE/'run_v1'
run.mkdir(exist_ok=False)  # Preserve every failed verdict; never overwrite.
for mutant in (0,1,2,3):
    binary=run/f'm{mutant}.vvp'
    cmd=['iverilog','-g2012','-s','tb_guard_fifo_sram',f'-DOT_HOST_GUARD_SRAM_MUTANT={mutant}','-DOT_HOST_GUARD_SRAM_DEFAULT=1','-o',str(binary),*map(str,sources)]
    build=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (run/f'm{mutant}.build.log').write_text(build.stdout)
    assert build.returncode==0,build.stdout
    result=subprocess.run(['vvp',str(binary)],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (run/f'm{mutant}.log').write_text(result.stdout)
    passed=result.returncode==0 and 'PASS cycles=100140' in result.stdout
    record['runs'].append({'mutant':mutant,'exit_code':result.returncode,'expected':'PASS' if mutant==0 else 'FAIL','observed':'PASS' if passed else 'FAIL','stdout':result.stdout})
    (HERE/'proof.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
    assert passed if mutant==0 else result.returncode!=0
    print(f'm{mutant}: exit={result.returncode} '+result.stdout.strip(),flush=True)
for p in run.glob('*.vvp'):p.unlink()
record['verdict']='PASS'
(HERE/'proof.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
