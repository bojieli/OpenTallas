#!/usr/bin/env python3
"""Compile real variable-context descriptor calendar+JEDEC core, independent native QK/PV answers."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.qwen_kv_die.static_qk_calendar import compile_calendar
from tools.qwen_static_schedule.kv_calendar import pv16_v_streams
from tools.qwen_kv_die.static_kv_calendar import physical_pc,sector
from controller_calendar_image import Run,compile_image
p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--mutant',type=int,default=0);p.add_argument('--pc',type=int,default=13);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
runs=[Run(10,command=1,layer_row=True,context_mode=1,context_descriptor=True),Run(80,command=(1<<31)|1),Run(300,burst=8,gap=2,mask=1,context_mode=1),Run(900,command=1,layer_row=True,context_mode=2,context_descriptor=True),Run(1000,command=(1<<31)|1),Run(1300,burst=8,gap=3,mask=1,context_mode=2)]
# Diagnostic conservative roots: K read +180 and V descriptor/go/read +300 vs old fixture.
# Throughput is NOT qualified; production compiler must price and derive actual roots.
Ts=[1,65,77,128,129,257,513,2048,4096,4097,4224,4225,4300,4500,6000,8191,8192,2,63,64,127,255,256,511,512,1024,2049,4095,4195,4501,6001,7000,8000,8156,8192,1]
with(a.out/'cases.txt').open('w')as out:
 for l,T in enumerate(Ts):
  s=(l//8)%4;g=l%8
  if l in (0,1,2,16,35):s=g=0
  img=compile_image(runs,deadline=2499,context=(T,s,g))
  eng=next(e for e in compile_calendar(T,21,34)['engines']if e['stack']==s and e['engine']==g)
  ks=[sector(x['t'],False)for x in eng['slots']]
  vs=[512+((t>>6)&1)*128+((t>>9)&15)*8+((t>>1)&7)for _,_,t in pv16_v_streams(T).get(physical_pc(s,g,0),[])]
  out.write(f'{T} {s} {g} {len(ks)+len(vs)}\n'+' '.join(map(str,ks+vs))+'\n')
  out.write(' '.join(str(int(i in img['events'] and img['events'][i]['mask']==1))for i in range(2500))+'\n')
(a.out/'image.hex').write_text(''.join(f'{w:032x}\n'for w in img['words']))
files=[f'rtl/qwen_sys/static_kv_20261014/{n}.sv'for n in ('qkd_controller_context_calendar','qkd_kv_context_shape','qkd_static_kv_return_calendar','ot_qkd_static_ctrl_pc_emb','ot_qkd_static_kv_timing')]+['rtl/test/qwen_static_kv/tb_context_controller.sv']
source_hashes={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest()for f in files}
binary=a.out/f'sim{a.mutant}'
subprocess.run(['iverilog','-g2012','-s','tb_context_controller',f'-Ptb_context_controller.MUT={a.mutant}',f'-Ptb_context_controller.PC={a.pc}','-o',str(binary)]+[str(ROOT/f)for f in files],check=True)
r=subprocess.run(['vvp',str(binary),f'+IMAGE={a.out}/image.hex',f'+CASES={a.out}/cases.txt'],capture_output=True,text=True)
(a.out/'run.log').write_text(r.stdout+r.stderr)
receipt=dict(mutant=a.mutant,pc=a.pc,exit=r.returncode,output=r.stdout,source_sha256=source_hashes,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),image_sha256=hashlib.sha256((a.out/'image.hex').read_bytes()).hexdigest(),expected_sha256=hashlib.sha256((a.out/'cases.txt').read_bytes()).hexdigest(),image_compiler_sha256=hashlib.sha256((ROOT/'tools/qwen_static_kv/controller_calendar_image.py').read_bytes()).hexdigest(),compiler_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scope='component actual calendar+PROFILE0 JEDEC core;36persistentlayers with changing T; excludes PHY/clock/other onchip/native chip')
(a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2));raise SystemExit(r.returncode)
