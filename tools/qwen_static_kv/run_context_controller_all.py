#!/usr/bin/env python3
"""Bounded two-worker Icarus component proof across 32 physical refresh straps, plus deliberate failures."""
import argparse,concurrent.futures,json,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
runner=Path(__file__).with_name('run_context_controller.py')
def case(case):
 pc,mut=case;out=a.out/f'pc{pc}_mut{mut}';out.mkdir(exist_ok=True)
 r=subprocess.run([sys.executable,str(runner),str(out),'--pc',str(pc),'--mutant',str(mut)],capture_output=True,text=True)
 (out/'driver.log').write_text(r.stdout+r.stderr)
 rec=json.loads((out/'receipt.json').read_text())if(out/'receipt.json').is_file()else {'error':r.stderr}
 return dict(pc=pc,mutant=mut,expected_exit=0 if mut==0 else 1,actual_exit=r.returncode,receipt=rec)
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
 results=list(pool.map(case,[(pc,0)for pc in range(32)]+[(13,m)for m in (1,2,3,4,5)]))
okay=all((r['actual_exit']==0)==(r['mutant']==0) and ('PASS context controller' if r['mutant']==0 else 'FAIL context controller') in r['receipt'].get('output','') and len(r['receipt'].get('binary_sha256',''))==64 for r in results)
(a.out/'summary.json').write_text(json.dumps(dict(passed=okay,results=results,scope='component variable-context calendar+realPROFILE0controller, not integrated die'),indent=2)+'\n')
print(json.dumps(dict(passed=okay,results=[{k:v for k,v in r.items()if k!='receipt'}for r in results]),indent=2));raise SystemExit(0 if okay else 1)
