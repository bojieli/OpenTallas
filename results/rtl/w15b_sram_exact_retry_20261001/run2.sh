#!/bin/bash
set -euo pipefail
export W15_BUILD=/home/ubuntu/w15bwork/codex_sram_attempt2
export W15_VEC="$1"
export TMPDIR=/home/ubuntu/w15bwork/codex_sram_attempt2/tmp
mkdir -p "$TMPDIR"
test -z "$(git status --porcelain)"
test -f "$2"
python3 - "$W15_VEC" <<'CHECK'
import pathlib,json,hashlib,sys
for n in ['l0w32','sweepw32']:
 p=pathlib.Path(sys.argv[1])/n;m=json.loads((p/'manifest.json').read_text())
 for f,h in m['images_sha256'].items():assert hashlib.sha256((p/f).read_bytes()).hexdigest()==h
print('INPUT_PREFLIGHT_PASS',flush=True)
CHECK
python3 tools/w15_collectives.py campaign --config v41ss_lm_w32 --config v41ss_lm_w32_sweep --ncal 24 --nmeas 12 --out results/rtl/w15b_sram_exact_retry_20261001/campaign.json
python3 "$2"
