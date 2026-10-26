#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
R=/srv/opentallas-scratch2/claude/codex-head0733/bf_gate
bash "$R/bench_gold/run_bench.sh" "$R/gold" gold 30000
bash "$R/bench/run_bench.sh" "$R/source" gate 30000
bash "$R/bench/run_bench.sh" "$R/mutant" mutant 30000
python3 - <<'PY'
from pathlib import Path
import json
r=Path('/srv/opentallas-scratch2/claude/codex-head0733/bf_gate')
a=(r/'bench_gold/gold/out.txt').read_text().splitlines();b=(r/'bench/gate/out.txt').read_text().splitlines();c=(r/'bench/mutant/out.txt').read_text().splitlines()
assert len(a)==len(b)==len(c)==30000
wrong=[i for i,(x,y) in enumerate(zip(a,b)) if x!=y];mut=[i for i,(x,y) in enumerate(zip(a,c)) if x!=y]
out={'edges':len(a),'mismatches':len(wrong),'mutant_mismatches':len(mut),'mutant_first':mut[0] if mut else None,'added_cycles':0,'verdict':'PASS' if not wrong and mut else 'FAIL'}
(r/'receipt.json').write_text(json.dumps(out,indent=2)+'\n');print(out)
assert out['verdict']=='PASS'
PY
