#!/usr/bin/env python3
"""Materialize exact revision sources for this receipt; run only in an empty stage."""
import hashlib,json,subprocess,sys
from pathlib import Path
packet=Path(__file__).resolve().parent
dst=Path(sys.argv[1]);dst.mkdir(parents=True,exist_ok=True)
rows=json.loads((packet/'source_manifest.json').read_text())
for row in rows:
    data=(subprocess.check_output(['git','show',row['rev']+':'+row['path']])
          if 'rev' in row else (packet/'tb_dma_integrated.sv').read_bytes())
    assert hashlib.sha256(data).hexdigest()==row['sha256'],row
    target=dst/row['file'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
for name in ['run.sh','sources.f','source_manifest.json']:
    (dst/name).write_bytes((packet/name).read_bytes())
