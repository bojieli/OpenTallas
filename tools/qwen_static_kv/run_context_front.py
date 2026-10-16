#!/usr/bin/env python3
"""Actual partial-block front plus actual group calendar against native consumer streams."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.qwen_kv_die.static_qk_calendar import compile_calendar
from tools.qwen_static_schedule.kv_calendar import pv16_v_streams
from tools.qwen_kv_die.static_kv_calendar import physical_pc,sector
p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--mutant',type=int,default=0);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
Ts=[1,2,7,8,9,15,16,17,31,32,33,63,64,65,77,127,128,129,255,256,257,511,512,513,2048,4096,4097,4224,4225,4300,4500,6000,8191,8192]
with(a.out/'cases.txt').open('w')as out:
 for T in Ts:
  vs=pv16_v_streams(T)
  for eng in compile_calendar(T,21,34)['engines']:
   s,g=eng['stack'],eng['engine'];ks=[sector(x['t'],False)for x in eng['slots']]
   v=[512+((t>>6)&1)*128+((t>>9)&15)*8+((t>>1)&7)for _,_,t in vs.get(physical_pc(s,g,0),[])]
   out.write(f'{T} {s} {g} {len(ks)} {len(v)}\n'+' '.join(map(str,ks))+'\n'+' '.join(map(str,v))+'\n')
files=[f'rtl/qwen_sys/static_kv_20261014/{n}.sv'for n in ('qkd_kv_hbm_context_front','qkd_kv_hbm_elastic_front','qkd_kv_context_front_cal')]+['rtl/test/qwen_static_kv/tb_context_front.sv']
hashes={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest()for f in files};binary=a.out/'sim'
subprocess.run(['iverilog','-g2012','-s','tb_context_front',f'-Ptb_context_front.MUT={a.mutant}','-o',str(binary)]+[str(ROOT/f)for f in files],check=True)
r=subprocess.run(['vvp',str(binary),f'+CASES={a.out}/cases.txt'],capture_output=True,text=True)
(a.out/'run.log').write_text(r.stdout+r.stderr)
rec=dict(mutant=a.mutant,exit=r.returncode,output=r.stdout,source_sha256=hashes,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),expected_sha256=hashlib.sha256((a.out/'cases.txt').read_bytes()).hexdigest(),scope='actual partial-block front/groupcalendar component; ideal corrected input boundary; noPHY/ring/physical qualification')
(a.out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec,indent=2));raise SystemExit(r.returncode)
