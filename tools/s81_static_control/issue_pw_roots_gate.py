#!/usr/bin/env python3
"""Exact split-PW-root boot/runtime behavior against immutable actual v2b.

Use actual128 rows, 13 engines, two contexts and all ten fault modes. Frozen
v2b defines reference edges; no behavioral scheduler replaces the target.
"""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 a=argparse.ArgumentParser();a.add_argument('out',type=Path);a=a.parse_args();o=a.out.resolve();o.mkdir(parents=True,exist_ok=True)
 sys.path.insert(0,str(ROOT/'tools/s81_static_control'));from program import encode_program
 rows=[dict(engine=i%13,arg=0x010203+i*0x001523,issue=i,done=i+3)for i in range(126)]+[dict(engine=14,arg=0,issue=129,done=0),dict(engine=15,arg=0,issue=130,done=0)]
 (o/'program.hex').write_text(''.join(f"{w['word']:09x}\n"for w in encode_program(rows,7,1)['writes']))
 s=ROOT/'rtl/dsrom_sys/s81_static_control';fixture=s/'test/tb_s81_fixed_issue.sv'
 trace=(s/'test/tb_s81_fixed_issue_trace.sv').read_text().replace('tick>=990','tick>=0');(o/'all_edges.sv').write_text(trace)
 sources={'reference':s/'test/ot_s81_fixed_issue_v2b_frozen.sv','candidate':s/'ot_s81_fixed_issue.sv'}
 for role,p in sources.items():
  cmd=['iverilog','-g2012']+(['-DOT_S81_ISSUER_SPLIT_PW']if role=='candidate'else[])+['-s','tb_s81_fixed_issue','-s','tb_s81_fixed_issue_trace','-o',str(o/role),str(p),str(fixture),str(o/'all_edges.sv')]
  subprocess.run(cmd,check=True,cwd=o)
 cases=[]
 for mode in range(10):
  traces={}
  for role in sources:
   r=subprocess.run(['vvp','-n',str(o/role),f'+mode={mode}'],cwd=o,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(o/f'{role}_{mode}.log').write_text(r.stdout)
   if r.returncode!=0 or f'S81_FIXED mode={mode}'not in r.stdout:raise RuntimeError(r.stdout[-3000:])
   traces[role]=[x for x in r.stdout.splitlines()if x.startswith('T ')]
  if traces['reference']!=traces['candidate']:raise RuntimeError('Actual all-edge mismatch mode '+str(mode))
  cases.append(dict(mode=mode,edges=len(traces['candidate']),PASS=True));print(json.dumps(cases[-1]),flush=True)
 mutants=[]
 for m in [1,2]:
  r=subprocess.run(['vvp','-n',str(o/'candidate'),'+mode=0',f'+root_mut={m}'],cwd=o,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);p=o/f'root_stop_{m}.log';p.write_text(r.stdout)
  if r.returncode==0 or 'FATAL:'not in r.stdout:raise RuntimeError('Root stop escaped '+str(m))
  mutants.append(dict(root=['clk','clk_pw'][m-1],exit_code=r.returncode,log_sha256=sha(p),PASS=True))
 receipt=dict(scope=__doc__,source_sha256={str(p.relative_to(ROOT)):sha(p)for p in [*sources.values(),fixture]},proof_sha256=sha(Path(__file__)),cases=cases,root_stop_mutants=mutants,seal_to_armed_edges=131,initialization_edges_added_vs_v2b=0,runtime_edges_added=0,physical_qualified=False)
 (o/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print('ISSUE_PW_ROOTS PASS actual boot/full128row runtime, all10modes/all1300edges and2root-stop mutants',flush=True)
if __name__=='__main__':main()
