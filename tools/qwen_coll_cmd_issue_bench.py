#!/usr/bin/env python3
"""Check actual issuer calendar row/tag completeness and unchanged fixed issue time."""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--mutant',action='store_true');a=p.parse_args()
r=Path(__file__).resolve().parents[1];out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
src=[r/x for x in ('rtl/qwen_sys/static_schedule_20261014/ot_qwen_fixed_issue.sv','rtl/rom/ot_coll_cmd_issue.sv','rtl/test/tb_coll_cmd_issue.sv')]
b=subprocess.run(['verilator','--binary','--timing','-Wno-fatal','--top-module','tb_coll_cmd_issue','--Mdir',str(out/'obj'),'-j','2',*(['+define+OT_COLL_ISSUE_MUT_HALF_LOADED'] if a.mutant else []),*[str(x) for x in src]],capture_output=True,text=True)
(out/'build.log').write_text(b.stdout+b.stderr);b.check_returncode()
records=[]
for omit in ((2,) if a.mutant else (0,1,2)):
 q=subprocess.run([str(out/'obj/Vtb_coll_cmd_issue'),f'+OMIT={omit}'],capture_output=True,text=True)
 (out/f'omit{omit}.log').write_text(q.stdout+q.stderr);print(q.stdout.strip(),flush=True)
 records.append({'omit':omit,'rc':q.returncode,'output':q.stdout})
 if a.mutant:
  assert q.returncode!=0 and 'completeness omit=2 fault=0' in q.stdout, 'mutant was not detected at the completeness check'
 else:q.check_returncode()
(out/'record.json').write_text(json.dumps({'mutant':a.mutant,'cases':records,'sources':{str(x.relative_to(r)):hashlib.sha256(x.read_bytes()).hexdigest() for x in src}},indent=2)+'\n')
