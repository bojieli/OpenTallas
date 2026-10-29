#!/usr/bin/env python3
"""Copy reached immutable predecessor source inputs into an owned worktree."""
import json,shutil,sys
from pathlib import Path
old=Path(sys.argv[1]).resolve();own=Path(sys.argv[2]).resolve();recipe=Path(sys.argv[3]);queue=[old/recipe];seen=set();copied=[]
def strings(o):
 if isinstance(o,str):yield o
 elif isinstance(o,dict):
  for v in o.values():yield from strings(v)
 elif isinstance(o,list):
  for v in o:yield from strings(v)
while queue:
 p=queue.pop().resolve()
 if p in seen or not p.is_file() or not p.is_relative_to(old):continue
 seen.add(p);rel=p.relative_to(old);dest=own/rel
 if not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest);copied.append(str(rel))
 if p.suffix=='.json':
  try:d=json.load(open(p))
  except (ValueError,OSError):continue
  for v in strings(d):
   if '/' not in v and not v.endswith(('.json','.sv','.v','.f')):continue
   for q in [old/v,p.parent/v]:
    if q.is_file():queue.append(q);break
print(json.dumps(dict(reached=len(seen),copied=len(copied),files=copied)))
