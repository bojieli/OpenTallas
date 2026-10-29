#!/usr/bin/env python3
"""Materialize exact composed event and its reached pin documents in an owned source tree."""
import hashlib,json,shutil,sys,os
from pathlib import Path
S=Path(sys.argv[1]).resolve();D=Path(sys.argv[2]).resolve();D.mkdir(parents=True,exist_ok=True)
C=D.parent/'cores';C.mkdir(exist_ok=True)
p=json.load(open(S/'plan.json'));n=0;docs={}
for t in p['partition_types'].values():
 for h in t.get('hard_cores',[]):
  if not h.get('pins_file'):continue
  f=(S/h['pins_file']).resolve();b=f.read_bytes();sha=hashlib.sha256(b).hexdigest()[:12];fn=f.stem+'_'+sha+f.suffix
  (C/fn).write_bytes(b);h['pins_file']='../cores/'+fn;n+=1;docs[fn]=sha
# Rebase canonical inherited census rather than dropping mandatory coverage.
W=D.parents[2]
for c in p.get('census', []):
 for key in ['rows','map','bitcon']:
  if c.get(key):
   f=(S/c[key]).resolve()
   if not f.is_file(): f=W/'physical/die_plan/qwen_kvsys'/c[key]
   assert f.is_file(),f
   c[key]=os.path.relpath(f,D)
(D/'plan.json').write_text(json.dumps(p,indent=1)+'\n')
for f in ['sidecar.json','regions_ca.json','straps.json']:shutil.copyfile(S/f,D/f)
shutil.copytree(S/'latency',D/'latency',dirs_exist_ok=True)
(D.parent/'pin_materialization.json').write_text(json.dumps(dict(core_slots=n,documents=docs),indent=1)+'\n')
print('MATERIALIZED',n,'core slots',len(docs),'exact pin documents')
