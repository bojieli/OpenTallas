#!/usr/bin/env python3
"""Run the phase gate; accepted mutants require observed wrong words or RTL fault."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--binary',type=Path,required=True);p.add_argument('--vectors',type=Path,required=True)
p.add_argument('--out',type=Path,required=True);p.add_argument('--stall',type=int,default=0)
p.add_argument('--mutant',choices=['none','q_order','context','group','precision','drop_k'],default='none')
p.add_argument('--max-cycles',type=int,default=100000)
a=p.parse_args()
m=json.loads((a.vectors/'phase_meta.json').read_text())
for name,sha in (m['input_hashes']|m['phase_hashes']).items():
    if hashlib.sha256((a.vectors/name).read_bytes()).hexdigest()!=sha: raise ValueError(name)
cmd=[str(a.binary.resolve()),str(a.vectors.resolve()),'16','750',str(a.max_cycles),str(a.stall),a.mutant]
r=subprocess.run(cmd,capture_output=True,text=True)
try: rec=json.loads(r.stdout.splitlines()[-1])
except (ValueError,IndexError): rec={}
pos=r.returncode==0 and rec.get('exact') and rec.get('scores')==m['score_words'] and rec.get('exponents')==m['exponent_words'] and rec.get('maxima')==4 and rec.get('denominators')==4
neg=r.returncode==1 and (rec.get('data_mismatches',0)>0 or rec.get('fault',0)>0)
record=dict(scope='QK_EXP_Z_PHASE_ONLY',passed=bool(pos if a.mutant=='none' else neg),mutant=a.mutant,command=cmd,exit_code=r.returncode,record=rec,phase_vectors=m,binary_sha256=hashlib.sha256(a.binary.read_bytes()).hexdigest(),stdout=r.stdout,stderr=r.stderr)
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:record[k] for k in ['passed','mutant','record']}))
raise SystemExit(0 if record['passed'] else 1)
