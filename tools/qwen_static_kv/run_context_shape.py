#!/usr/bin/env python3
"""Actual combinatorial hardware against independently enumerated native consumer calendars."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.qwen_kv_die.static_qk_calendar import compile_calendar
from tools.qwen_static_schedule.kv_calendar import pv16_v_streams
from tools.qwen_kv_die.static_kv_calendar import physical_pc,sector
p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
Ts=sorted(set([1,2,7,8,15,16,63,64,65,77,127,128,129,255,256,257,511,512,513,2048,4096,4097,4224,4225,4300,4500,6000,8191,8192]+[1+i*233 for i in range(36)]))
vectors=0
with(a.out/'cases.txt').open('w')as out:
 for T in Ts:
  ks=compile_calendar(T,21,34)['engines'];vs=pv16_v_streams(T)
  for eng in ks:
   s,g=eng['stack'],eng['engine']
   seqs=([sector(sl['t'],False) for sl in eng['slots']],
         [512+((t>>6)&1)*128+((t>>9)&15)*8+((t>>1)&7)for _,_,t in vs.get(physical_pc(s,g,0),[])])
   for v,seq in enumerate(seqs):
    for i,sec in enumerate(seq or [0]):
     # no output sector is meaningful for an empty stream
     out.write(f'{T} {s} {g} {v} {i} {len(seq)} {sec}\n');vectors+=1
sources=['rtl/qwen_sys/static_kv_20261014/qkd_kv_context_shape.sv','rtl/test/qwen_static_kv/tb_context_shape.sv']
results=[]
for mut in (0,1,2):
 binary=a.out/f'sim{mut}'
 subprocess.run(['iverilog','-g2012','-s','tb_context_shape',f'-Ptb_context_shape.MUT={mut}','-o',str(binary)]+[str(ROOT/s)for s in sources],check=True)
 r=subprocess.run(['vvp',str(binary),f'+CASES={a.out}/cases.txt'],capture_output=True,text=True)
 (a.out/f'mut{mut}.log').write_text(r.stdout+r.stderr)
 results.append(dict(mutant=mut,exit=r.returncode,output=r.stdout[-1500:]))
 if (r.returncode==0)!=(mut==0):raise SystemExit(results[-1])
receipt=dict(contexts=Ts,vectors=vectors,results=results,source_sha256={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest()for s in sources},scope='component actual geometry/count/end hardware; no controller/physical/native-chip qualification')
(a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
