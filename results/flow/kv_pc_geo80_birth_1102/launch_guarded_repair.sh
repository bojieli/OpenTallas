#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-pc-geo80-birth-1102
python3 - "$R" <<'PY'
from pathlib import Path
import hashlib,json,sys
r=Path(sys.argv[1]);p=r/'RUNTIME_READSET.json';raw=p.read_bytes()
expected='4fee4bc68ca8b46189a4bd65218b9fbc0ade9b930c0266410469c94b22e2fedf'
assert hashlib.sha256(raw).hexdigest()==expected,'runtime manifest changed'
x=json.loads(raw);d=r/'repair'
for rel,want in x['files'].items():
 assert hashlib.sha256((d/rel).read_bytes()).hexdigest()==want,rel
f=Path(x['launcher']['path'])
assert hashlib.sha256(f.read_bytes()).hexdigest()==x['launcher']['sha256'],'reviewed launcher changed'
assert not (r/'DISPATCH_STARTED').exists(),'one-shot entry already dispatched'
(r/'STAGED_GUARD.json').write_text(json.dumps(dict(status='PASS',runtime_readset_sha256=expected,files=len(x['files']),native_input_PG0='required inside canonical begin, not preclaimed'),indent=2)+'\n')
PY
exec bash "$R/prep/pc_geo80_repair.sh"
