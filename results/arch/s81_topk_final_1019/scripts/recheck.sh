#!/bin/bash
set -euo pipefail
cd src
export VL_EXTRA=-DOT_S81PH_SEL_INDEXED13
set +e
bash tools/s81_dv/layer_prog/bk/run_bk_layer.sh ../build_fanout ../bench/legacy ../bench/indexed13 ../bench/indexed13_ties ../bench/indexed13_zeros ../bench/indexed13_ninf ../bench/indexed13_corrupt ../bench/indexed13_early ../bench/indexed13_identity
set -e
python3 - <<'PY'
from pathlib import Path
import json
for d in Path('../bench').iterdir():
 if d.name=='default_reject':continue
 if not (d/'check_result.json').exists():continue
 r=json.loads((d/'check_result.json').read_text())
 assert r['pass_']==(d.name not in ('indexed13_corrupt','indexed13_early','indexed13_identity')),d
print('FANOUT_RECHECK PASS')
PY
