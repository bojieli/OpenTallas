#!/usr/bin/env python3
"""Read-only guard for exact frozen G7 source and existing hierarchical objects."""
import argparse,hashlib,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
def sha(q):
 h=hashlib.sha256()
 with q.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
m=json.loads(a.manifest.read_text());root=Path(m['root']);objects=root/'run/obj';fail=[];inputs={};reuse={};child_sources={}
for name,old in m['files'].items():
 q=Path(name)
 if not q.is_file():fail.append({'missing':name});continue
 now=sha(q);inputs[name]=now
 if now!=old['sha256']:fail.append({'mismatch':name,'expected':old['sha256'],'actual':now})
for vf in sorted(objects.glob('V*/*__verFiles.dat')):
 for line in vf.read_text().splitlines():
  if not line.startswith('S '):continue
  hit=re.search(r'"([^"\n]+)"$',line)
  if not hit:fail.append({'unparsed':str(vf),'line':line});continue
  q=Path(hit.group(1));name=str(q)
  if not q.is_file():fail.append({'missing_child_source':name});continue
  actual=sha(q);child_sources[name]=actual
  if name not in m['files']:
   # Verilator generated child boundary/compilation headers are allowed only
   # inside this immutable object directory, and are explicitly frozen below.
   if not q.is_relative_to(objects):fail.append({'unrecorded_child_source':name})
  elif actual!=m['files'][name]['sha256']:fail.append({'changed_child_source':name})
for d in sorted(objects.glob('V*')):
 if not d.is_dir():continue
 for q in sorted(d.rglob('*')):
  if q.is_file() and q.suffix in {'.a','.h','.sv','.mk','.dat'}:reuse[str(q)]={'sha256':sha(q),'bytes':q.stat().st_size}
if not reuse:fail.append({'error':'no reusable hierarchical objects'})
r={'status':'PASS' if not fail else 'REFUSED','original_manifest':sha(a.manifest),'frozen_inputs':inputs,'child_sources':child_sources,'reusable_files':reuse,'failures':fail,'scope':'child object reuse only; top must regenerate for new verification fixture'}
a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'status':r['status'],'inputs':len(inputs),'child_sources':len(child_sources),'reuse_files':len(reuse),'failures':fail},indent=2));raise SystemExit(bool(fail))
