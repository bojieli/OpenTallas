#!/usr/bin/env python3
"""Replay the exact hk5l geometry-only delta onto a compatible source candidate.
Fails before writing if any old field differs. Never substitutes the 21-type
physical trial for the 25-type source of record; fresh clock/CA remain required.
"""
import copy,json,sys
from pathlib import Path
p=Path(sys.argv[1]);out=Path(sys.argv[2]);d=json.load(open(Path(__file__).with_name('delta.json')))
a=json.load(open(p));b=copy.deepcopy(a);errors=[]
for path,old,new in d['fields']:
 if path=='/note':continue
 keys=path.strip('/').split('/');node=b
 try:
  for k in keys[:-1]:node=node[int(k)] if isinstance(node,list) else node[k]
  key=int(keys[-1]) if isinstance(node,list) else keys[-1]
  actual=node[key] if isinstance(node,list) else node.get(key)
  if actual!=old:errors.append(dict(path=path,expected=old,actual=actual));continue
  node[key]=new
 except (KeyError,IndexError,TypeError):errors.append(dict(path=path,error='missing source field'))
if errors:raise SystemExit(json.dumps({'status':'RECOMPOSE_REQUIRED','mismatches':errors},indent=1))
if out.exists():raise SystemExit('refuse to overwrite existing candidate')
out.write_text(json.dumps(b,indent=1)+'\n')
print(json.dumps({'status':'CANDIDATE_ONLY','parts':len(b['partitions']),'types':len(b['partition_types']),'data_cycles_added':0,'fresh_clock_CA':'REQUIRED'}))
