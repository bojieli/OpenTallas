#!/bin/bash
# Run on fleet. Requires the pinned compiler/ancillary sources described here.
set -euo pipefail
P=$(cd "$(dirname "$0")" && pwd)
R=$(cd "$P/../../../.." && pwd)
O=${1:?new output directory required}
cd "$P"
tar -xzf inputs.tar.gz
python3 - <<'PY'
import hashlib,json
from pathlib import Path
for row in json.loads(Path('inputs_manifest.json').read_text()):
 p=Path('inputs')/row['file']
 assert p.stat().st_size==row['size'] and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],p
PY
cd "$R"
python3 "$P/run_sourcepack.py" --out "$O" \
 --compute-stages "$P/inputs/compute_netlist_relay.json" --kv-stages "$P/inputs/kv_table.gen7.json" \
 --compute-die-v "$P/inputs/die.v" --compute-lanes "$P/inputs/fwd_lanes.json" \
 --compute-params "$P/inputs/die.v.params.json" \
 --compute-commit 0d4c9808fe7d2370185a4313e831b6f59f7a2f75 --kv-commit 4db097403
