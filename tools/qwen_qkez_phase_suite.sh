#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch/codex/qkez-phase-ee277
python3 - <<'PY'
import hashlib,json
from pathlib import Path
m=json.loads(Path('source_manifest.json').read_text())
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==sha for p,sha in m['files'].items())
PY
for vec in full8192 partial777 ties8192; do
 python3 tools/qwen_qkez_phase_vectors.py vectors/$vec > vectors/$vec/phase_build.log
 python3 tools/qwen_qkez_phase_run.py --binary obj/Vtb --vectors vectors/$vec --out receipts/${vec}_positive.json --stall 1 --trace-dir traces/$vec
 done
python3 tools/qwen_qkez_phase_run.py --binary obj/Vtb --vectors vectors/full8192 --out receipts/q_order.json --stall 1 --mutant q_order
python3 tools/qwen_qkez_phase_run.py --binary obj/Vtb --vectors vectors/full8192 --out receipts/context_return_tag.json --stall 1 --mutant context
python3 tools/qwen_qkez_phase_run.py --binary obj/Vtb --vectors vectors/ties8192 --out receipts/precision.json --stall 1 --mutant precision
python3 tools/qwen_qkez_phase_run.py --binary obj/Vtb --vectors vectors/full8192 --out receipts/drop_k_payload.json --stall 1 --mutant drop_k
