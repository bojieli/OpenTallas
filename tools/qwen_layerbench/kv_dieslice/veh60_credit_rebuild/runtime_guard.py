#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent
for row in json.loads((D/'runtime_inputs.json').read_text()):
 p=Path(row['path']);h=hashlib.sha256()
 with p.open('rb') as f:
  for data in iter(lambda:f.read(8<<20),b''):h.update(data)
 assert h.hexdigest()==row['sha256'],p
print('RUNTIME_INPUT_GUARD_PASS')
