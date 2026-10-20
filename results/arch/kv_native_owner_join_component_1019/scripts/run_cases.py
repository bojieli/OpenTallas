#!/usr/bin/env python3
"""Fleet-only runtime pickup: reuse the exact successful compiled object."""
import argparse,hashlib,json,pathlib,subprocess
p=argparse.ArgumentParser();p.add_argument('--cases',required=True);a=p.parse_args()
r=pathlib.Path.cwd();m=json.loads((r/'source_manifest.json').read_text())
if (r/'compile.rc').read_text().strip()!='0':raise SystemExit('original compile did not pass')
c=json.loads((r/'command.json').read_text())
if '5.050' not in c['verilator']:raise SystemExit('wrong original Verilator')
for row in m['sources']:
 if hashlib.sha256((r/row['path']).read_bytes()).hexdigest()!=row['sha256']:raise SystemExit('frozen source changed '+row['path'])
binary=r/'obj/Vnative_join_bench';binary_sha=hashlib.sha256(binary.read_bytes()).hexdigest()
for case in [int(x)for x in a.cases.split(',')]:
 log=r/f'case{case}.log';receipt=r/f'case{case}.receipt.json'
 if log.exists() or receipt.exists():raise SystemExit('preserve existing case evidence '+str(case))
 with log.open('wb')as f:rc=subprocess.run(['/usr/bin/time','-v',str(binary),f'+CASE={case}'],stdout=f,stderr=subprocess.STDOUT).returncode
 content=log.read_text(errors='replace');passed=rc==0 and 'NATIVE_JOIN_PASS FUNCTIONAL_ONLY' in content and '%Error' not in content
 receipt.write_text(json.dumps({'case':case,'exit':rc,'application_pass':passed,'binary_sha256':binary_sha,'source_manifest_sha256':hashlib.sha256((r/'source_manifest.json').read_bytes()).hexdigest(),'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),'scope':'FUNCTIONAL_ONLY; no rebuild'},indent=2)+'\n')
 if not passed:raise SystemExit(rc or 1)
print('RUNTIME_PICKUP_PASS; original compiled object reused')
