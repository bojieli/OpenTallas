#!/usr/bin/env python3
"""Same pin step as codex-kv-0822 run_place.sh: fresh constraints carry the exact source ODB sha256."""
import hashlib,json,sys
from pathlib import Path
n=Path(sys.argv[1]);p=n/'native_bound/constraints/constraints.json';d=json.load(open(p))
d['source_odb_sha256']=hashlib.sha256((n/'native_bound/native_source.odb').read_bytes()).hexdigest()
p.write_text(json.dumps(d,separators=(',',':'))+'\n');print('PINNED',d['source_odb_sha256'])
