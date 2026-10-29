#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-kv-0822
P=/srv/opentallas-scratch2/claude/die-kv-29-1029/venv/bin/python3
python3 - "$R" <<'PY'
from pathlib import Path
import json,hashlib,sys
r=Path(sys.argv[1]);p=r/'native_bound/constraints/constraints.json';d=json.load(open(p));d['source_odb_sha256']=hashlib.sha256((r/'native_bound/native_source.odb').read_bytes()).hexdigest();p.write_text(json.dumps(d,separators=(',',':'))+'\n')
PY
$P "$R/imp/plan_place.py" --inventory "$R/provider_cells_kv6.json" --constraints "$R/native_bound/constraints/constraints.json" --budget "$R/budget_kv6_node.json" --out "$R/proposal_native" > "$R/proposal_native.log" 2>&1
$P "$R/imp/preflight.py" --inventory "$R/provider_cells_kv6.json" --mapped "$R/provider_mapped_kv6.json" --placements "$R/proposal_native/placements.json" --proposal-constraints "$R/native_bound/constraints/constraints.json" --fresh-constraints "$R/native_bound/constraints/constraints.json" --bindings "$R/native_bound/bindings_native.json" --out "$R/native_bound/preflight.json" > "$R/native_bound/preflight.log" 2>&1
