import hashlib,json
from pathlib import Path
r=Path('/srv/opentallas-scratch/claude/codex-gl24-1020/fixtures')
for d in sorted(r.glob('L*')):
 files=json.loads((d/'files.json').read_text());ops=json.loads((d/'ops.json').read_text())
 for name,meta in files.items():assert hashlib.sha256((d/name).read_bytes()).hexdigest()==meta['sha256'],(d,name)
 for name,meta in ops.items():assert hashlib.sha256((d/('ops/'+name+'.bin')).read_bytes()).hexdigest()==meta['sha256'],(d,name)
 print('FIXTURE_SHA_PASS',d.name,len(files),len(ops))
