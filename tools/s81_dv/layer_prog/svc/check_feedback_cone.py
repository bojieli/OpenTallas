#!/usr/bin/env python3
"""Check the exercised feedback module bodies, including portable bench input.

The original sources.sha256 records all parsed source files. That read list
also contains unused native engines and is intentionally not this gate.
The module list below came from Verilator 5.050 --json-only elaboration of
the exact measured top, source list, parameters and bench.
"""
import hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
receipt=ROOT/'results/token_pass/svc_local_feedback_1113/elaborated_cone.json'
r=json.loads(receipt.read_text());errors=[]
for row in r['modules']:
 p=ROOT/row['path']
 text=p.read_text()
 m=re.search(r'(?m)^module\s+'+re.escape(row['name'])+r'\b[\s\S]*?\bendmodule\b',text)
 actual=hashlib.sha256(m.group().encode()).hexdigest()if m else None
 if actual!=row['sha256']:errors.append(row['path']+':'+row['name'])
tb=ROOT/r['portable_bench']['path']
if hashlib.sha256(tb.read_bytes()).hexdigest()!=r['portable_bench']['sha256']:errors.append(str(tb))
print('FEEDBACK_CONE '+('FAIL'if errors else'PASS')+' modules='+str(len(r['modules']))+' mismatches='+str(errors))
sys.exit(bool(errors))
