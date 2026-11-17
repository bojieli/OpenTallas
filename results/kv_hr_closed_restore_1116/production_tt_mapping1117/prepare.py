#!/usr/bin/env python3
"""prepare.py NEW_RUN_DIR PINNED_LIBRARY_DIR; then cd NEW_RUN_DIR && bash run.sh."""
from pathlib import Path
import hashlib,json,shutil,sys,tarfile
here=Path(__file__).resolve().parent
out=Path(sys.argv[1]);libs=Path(sys.argv[2]);meta=json.loads((here/'inventory.json').read_text())
for name,sha in meta['libraries_sha256'].items():
 if hashlib.sha256((libs/name).read_bytes()).hexdigest()!=sha:raise ValueError('library SHA mismatch: '+name)
out.mkdir(parents=True,exist_ok=False)
with tarfile.open(here/'sources.tar.gz') as t:
 for member in t.getmembers():
  q=Path(member.name)
  if not member.isfile() or q.is_absolute() or '..' in q.parts:raise ValueError(member.name)
  dst=out/q;dst.parent.mkdir(parents=True,exist_ok=True)
  with t.extractfile(member) as src,open(dst,'wb') as dest:dest.write(src.read())
for shape in ['context','baseline']:
 for name in meta['libraries_sha256']:shutil.copy2(libs/name,out/shape/name)
print('cd',out,'&& bash run.sh')
