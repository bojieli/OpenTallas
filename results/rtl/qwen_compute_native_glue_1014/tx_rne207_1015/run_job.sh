#!/usr/bin/env bash
set -euo pipefail
python3 - <<'CHECK'
import json,hashlib,pathlib
for p,h in json.loads(pathlib.Path('source_hashes.json').read_text()).items():assert hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==h,p
print('SOURCE_HASHES_PASS')
CHECK
bash physical/qwen_tx_rne_retime_1015/run_proofs.sh out
