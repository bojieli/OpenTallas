#!/bin/bash
set -euo pipefail
q=/srv/opentallas-scratch2/claude/codex-local-entry-0841
src=/srv/opentallas-scratch2/claude/head-start-2
python3 "$q/src/tools/clk/ot_clk.py" local-entry --physical "$src/in/final5/driven/physical.json" --stages "$src/in/final5/start_stages.json" --plan "$src/in/plan_spine_raw_rx_tx.json" --ctree "$src/in/final5/clock" --lef "$src/in/cells.lef" --out "$q/physical_lc_source2.json"
python3 - <<'PY'
import json,hashlib
from pathlib import Path
p=Path('/srv/opentallas-scratch2/claude/codex-local-entry-0841')
a=Path('/srv/opentallas-scratch2/claude/head-start-2/lc/physical_lc.json').read_bytes();b=(p/'physical_lc_source2.json').read_bytes()
assert a==b,'changed exact production geometry or output fields'
d=json.loads(b)
r=dict(status='BYTE_IDENTICAL',buffers=len(d['stage_clock_drivers']),sha256=hashlib.sha256(b).hexdigest(),flops_added=0,cycles_added=0)
(p/'compare.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r))
PY
