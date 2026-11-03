#!/bin/bash
set -euo pipefail
python3 - <<'INNER'
from pathlib import Path
import hashlib,json
r=Path('/srv/opentallas-scratch2/claude/codex-pc-geo80-birth-1102');d=r/'grt_only';p=r/'FRESH_GRT_RUNTIME.json'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='befb52cbe3a5c4f06551e3fedab174e379feaf9aa2743a7f9bd510a3d866d943','manifest changed'
j=json.loads(p.read_text())
for n,h in j['files'].items():
 assert hashlib.sha256((d/n).read_bytes()).hexdigest()==h,n
with (r/'FRESH_GRT_DISPATCH_STARTED').open('x') as f:f.write('guard PASS; native inputPG0 required in real begin, not preclaimed\n')
INNER
exec bash /srv/opentallas-scratch2/claude/codex-pc-geo80-birth-1102/grt_only/pc_native_grt_only.sh
