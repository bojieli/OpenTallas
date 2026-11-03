#!/bin/bash
set -euo pipefail
python3 - <<'INNER'
from pathlib import Path
import hashlib,json
r=Path('/srv/opentallas-scratch2/claude/codex-pc-geo80-birth-1102');d=r/'drt_only';p=r/'DRT_RUNTIME.json'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='d578dc8dd44b5566c75570aadc01390c9082094ad4f4bac462f42a4e9e6b55f8','manifest changed'
j=json.loads(p.read_text())
for n,h in j['files'].items():assert hashlib.sha256((d/n).read_bytes()).hexdigest()==h,n
assert not list((d/'run/results').glob('**/5_2*')),'existing route output'
with (r/'DRT_DISPATCH_STARTED').open('x') as f:f.write('exact current saved GRT; inputPG0 and zero-event scope required, not preclaimed\n')
INNER
exec bash /srv/opentallas-scratch2/claude/codex-pc-geo80-birth-1102/drt_only/run_drt_only.sh
