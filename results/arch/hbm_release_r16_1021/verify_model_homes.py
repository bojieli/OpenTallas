#!/usr/bin/env python3
"""Fail closed when GEN did not realize a selected source-pinned placement model."""
import json,sys,hashlib
from pathlib import Path
model,manifest,out=map(Path,sys.argv[1:]);m=json.load(open(model));a=json.load(open(manifest));bad=[]
for row in m['placement_checks']:
 n=row['instance'];actual=a.get('placement',{}).get(n);expected=row['after']
 if actual is None:bad.append(dict(instance=n,missing=True));continue
 for k in ['m','o','x','y','w','h']:
  ok=abs(actual[k]-expected[k])<.001 if isinstance(actual[k],(int,float)) else actual[k]==expected[k]
  if not ok:bad.append(dict(instance=n,field=k,expected=expected[k],actual=actual[k]))
r=dict(status='FAIL' if bad or a.get('placement_problems') else 'PASS',intended=len(m['placement_checks']),mismatches=bad,placement_problems=a.get('placement_problems'),model_sha256=hashlib.sha256(model.read_bytes()).hexdigest(),manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),scope='Actual selected homes/source-body consistency only; no capacity/native/physical qualification')
out.write_text(json.dumps(r,indent=2)+'\n');print('SELECTED_MODEL_HOMES',r['status'],'intended',r['intended'],'mismatches',len(bad));sys.exit(0 if r['status']=='PASS' else 25)
