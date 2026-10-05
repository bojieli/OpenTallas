#!/usr/bin/env python3
"""Bounded physical SRAM-model gate; synthetic data on issued synthetic addresses."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
try:
 from tools.qwen_g4_trace_banks import load_csv
except ModuleNotFoundError:
 from qwen_g4_trace_banks import load_csv
ROOT=Path(__file__).resolve().parents[1]
SOURCES=['rtl/test/tb_qwen_g4_vm_skew_candidate.sv','rtl/physical/ot_qwen_g4_vm_skew_candidate.sv','physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v']
def run():
 with tempfile.TemporaryDirectory(prefix='qwen-skew-') as d:
  exe=str(Path(d)/'sim')
  subprocess.run(['iverilog','-g2012','-s','tb_qwen_g4_vm_skew_candidate','-o',exe,*SOURCES],cwd=ROOT,check=True,capture_output=True,text=True)
  rows=load_csv(ROOT/'results/contracts/qwen_g4_boundary_trace.csv.gz')
  mem=[0x3f000000+i for i in range(65536)]; lines=[]
  for t,row in enumerate(rows):
   re=we=ra=wa=mask=data=expected=0
   for x in row['vm_reads']:
    g,a=x['group'],x['addr'];re|=1<<g;ra|=a<<(16*g);expected|=mem[a]<<(32*g)
   for x in row['vm_writes']:
    g,a,m=x['group'],x['addr'],x['mask'];we|=1<<g;wa|=a<<(12*g);mask|=m<<(16*g)
    for lane in range(16):
     value=0x41000000+t*64+g*16+lane;data|=value<<(512*g+32*lane)
     if m>>lane&1:mem[a*16+lane]=value
   packed=0
   for value,width in [(re,4),(we,4),(ra,64),(wa,48),(mask,64),(data,2048),(expected,128)]:packed=(packed<<width)|value
   lines.append(f'{packed:0590x}')
  trace=Path(d)/'trace.hex';trace.write_text('\n'.join(lines)+'\n')
  r=subprocess.run(['vvp',exe,f'+TRACE={trace}',f'+NTRACE={len(rows)}'],cwd=ROOT,check=True,capture_output=True,text=True)
  if 'PASS G4 skew' not in r.stdout:raise RuntimeError(r.stdout)
  return {'status':'PASS_candidate_physical_macro_model_only','scope':'not production-core integration, no physical timing, synthetic nonzero data',
   'logical_words':4096,'checked_lane_reads':16384,'macro_instances':32,'capacity_bytes':262144,
   'accepted_trace_cycles':len(rows),'trace_sha256':hashlib.sha256((ROOT/'results/contracts/qwen_g4_boundary_trace.csv.gz').read_bytes()).hexdigest(),
   'checks':['synthetic issued trace with nonzero generated data','full capacity','masked disjoint same-word merge','read-before-write','atomic overlapping write fault','conflicting read fault'],
   'stdout':r.stdout,'source_pins':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES}}
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args();s=json.dumps(run(),indent=2)+'\n'
 if a.output:a.output.write_text(s)
 else:print(s,end='')
