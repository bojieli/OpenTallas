#!/usr/bin/env python3
"""Actual embedding RTL positives and observed data/address-alias negatives."""
import argparse, hashlib, json, subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--binary',type=Path,required=True);p.add_argument('--program',type=Path,required=True)
p.add_argument('--vectors',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
a.out.mkdir(parents=True,exist_ok=False)
records=[]
for mode in ('none','code','alias','word'):
    r=subprocess.run([str(a.binary),str(a.program),str(a.vectors),str(a.out/mode),mode],capture_output=True,text=True)
    (a.out/f'{mode}.stdout').write_text(r.stdout);(a.out/f'{mode}.stderr').write_text(r.stderr)
    ok=(r.returncode==2 and 'actual accepted1024-bit instruction differs' in r.stderr) if mode=='word' else r.returncode==(0 if mode=='none' else 1) and 'TOTAL_ERRORS ' in r.stdout
    records.append({'mode':mode,'exit':r.returncode,'passed_expected_verdict':ok,'stdout':r.stdout})
    print(r.stdout,end='');print('EXPECTED_VERDICT',mode,ok,flush=True)
report={'scope':'Actual NW18 embedding2-word program, real checkpoint codes and VM commits; no layer/head/token completion',
        'binary_sha256':hashlib.sha256(a.binary.read_bytes()).hexdigest(),
        'program_sha256':hashlib.sha256(a.program.read_bytes()).hexdigest(),'records':records,
        'actual_exports_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (a.out/'none').glob('*.hex')},
        'passed':all(r['passed_expected_verdict'] for r in records)}
(a.out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
raise SystemExit(0 if report['passed'] else 1)
