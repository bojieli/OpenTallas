#!/usr/bin/env python3
"""Fleet-only reviewed initial cohort; one build, four runtime cases."""
import hashlib,json,os,pathlib,subprocess,sys,time
root=pathlib.Path.cwd();version=subprocess.check_output([os.environ.get('VERILATOR','verilator'),'--version'],text=True).strip()
if '5.050' not in version:raise SystemExit('requires exact Verilator5.050; got '+version)
manifest=json.loads((root/'source_manifest.json').read_text())
for r in manifest['sources']:
 if hashlib.sha256((root/r['path']).read_bytes()).hexdigest()!=r['sha256']:raise SystemExit('source hash mismatch '+r['path'])
if (root/'compile.log').exists():raise SystemExit('preserve earlier compile.log; use new run directory')
cmd=[os.environ.get('VERILATOR','verilator'),'--binary','--timing','--top-module','native_join_bench','-j','4','--Mdir','obj','--x-initial','unique','--x-assign','unique','-DOT_MEM_NO_INIT','-Wno-fatal','-f','sources.f']
(root/'command.json').write_text(json.dumps({'command':cmd,'verilator':version,'mem_GB':16,'threads':4,'disk_GB':20,'scope':'FUNCTIONAL_ONLY common-clock fixture; no production calendar'},indent=2)+'\n')
with (root/'compile.log').open('wb') as log:rc=subprocess.run(['/usr/bin/time','-v']+cmd,stdout=log,stderr=subprocess.STDOUT).returncode
(root/'compile.rc').write_text(str(rc)+'\n')
if rc:raise SystemExit(rc)
receipts=[]
for case in range(4):
 with (root/f'case{case}.log').open('wb') as log:rc=subprocess.run(['/usr/bin/time','-v','obj/Vnative_join_bench',f'+CASE={case}'],stdout=log,stderr=subprocess.STDOUT).returncode
 content=(root/f'case{case}.log').read_text(errors='replace')
 passed=rc==0 and 'NATIVE_JOIN_PASS FUNCTIONAL_ONLY' in content and '%Error' not in content
 receipts.append({'case':case,'exit':rc,'application_pass':passed,'log_sha256':hashlib.sha256((root/f'case{case}.log').read_bytes()).hexdigest()})
 (root/'initial_receipt.json').write_text(json.dumps({'kind':'FUNCTIONAL_ONLY','cases':receipts,'production_H':None,'remaining':'NO_NATIVE, health failure, cancellation, duplicate client errors and nine causal categories pending'},indent=2)+'\n')
 if not passed:raise SystemExit(rc or 1)
print('INITIAL_COHORT_PASS cases=4; remaining source/causal requirements OPEN')
