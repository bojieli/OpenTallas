#!/usr/bin/env python3
"""Check actual issuer calendar row/tag completeness and unchanged fixed issue time."""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--mutant',action='store_true');p.add_argument('--four-state',action='store_true');a=p.parse_args()
r=Path(__file__).resolve().parents[1];out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
src=[r/x for x in ('rtl/qwen_sys/static_schedule_20261014/ot_qwen_fixed_issue.sv','rtl/rom/ot_coll_cmd_issue.sv','rtl/test/tb_coll_cmd_issue.sv')]
b=subprocess.run((['iverilog','-g2012','-s','tb_coll_cmd_issue','-o',str(out/'sim')]+(['-DOT_COLL_ISSUE_MUT_HALF_LOADED'] if a.mutant else [])+[str(x) for x in src]) if a.four_state else ['verilator','--binary','--timing','-Wno-fatal','--top-module','tb_coll_cmd_issue','--Mdir',str(out/'obj'),'-j','2',*(['+define+OT_COLL_ISSUE_MUT_HALF_LOADED'] if a.mutant else []),*[str(x) for x in src]],capture_output=True,text=True)
(out/'build.log').write_text(b.stdout+b.stderr);b.check_returncode()
records=[]
for omit,reload in ([(2,0)] if a.mutant else [(0,0),(1,0),(2,0),(0,1)]):
 q=subprocess.run((['vvp',str(out/'sim')] if a.four_state else [str(out/'obj/Vtb_coll_cmd_issue')])+[f'+OMIT={omit}',f'+RELOAD={reload}'],capture_output=True,text=True)
 (out/f'omit{omit}-reload{reload}.log').write_text(q.stdout+q.stderr);print(q.stdout.strip(),flush=True)
 records.append({'omit':omit,'reload':reload,'rc':q.returncode,'output':q.stdout})
 if a.mutant:
  assert q.returncode!=0 and ('completeness omit=2 fault=0' in q.stdout or 'image readiness omit=2 ready=1' in q.stdout), 'mutant was not detected at the completeness check'
 else:q.check_returncode()
(out/'record.json').write_text(json.dumps({'four_state':a.four_state,'mutant':a.mutant,'cases':records,'sources':{str(x.relative_to(r)):hashlib.sha256(x.read_bytes()).hexdigest() for x in src}},indent=2)+'\n')
