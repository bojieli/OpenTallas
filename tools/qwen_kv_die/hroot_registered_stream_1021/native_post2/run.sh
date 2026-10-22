#!/usr/bin/env bash
set -euo pipefail
python3 - <<'INNER'
from pathlib import Path
import re,json,hashlib
p=Path('qkd_host_native_engine_n32.sv');raw=p.read_bytes();norm,n=re.subn(rb'(?m)^`timescale[^\n]*\n',b'',raw);assert n==1
assert raw.splitlines(keepends=True)[1:]==norm.splitlines(keepends=True)
Path('native_no_timescale.v').write_bytes(norm)
Path('normalization.json').write_text(json.dumps(dict(reason='frozen structural parser does not consume leading timeunit directive',removed_directives=n,original_sha256=hashlib.sha256(raw).hexdigest(),structural_projection_sha256=hashlib.sha256(norm).hexdigest(),all_other_bytes_identical=True),indent=2)+'\n')
INNER
args=(python3 native_census.py --netlist native_no_timescale.v --top qkd_host_native_engine_n32 --out native_raw.json)
for f in libs/*.lib; do args+=(--liberty "$f"); done
"${args[@]}" >native_raw.log 2>&1
