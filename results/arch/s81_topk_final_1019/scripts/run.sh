#!/bin/bash
set -euo pipefail
cd src
B=../bench
mkdir -p "$B"
for mode in legacy indexed13; do
 args=()
 [ "$mode" = legacy ] || args=(--indexed13)
 python3 tools/s81_dv/layer_prog/lower_bk.py gen --fixtures ../fx --job topk_final --out "$B/$mode" "${args[@]}"
done
for mut in corrupt early; do
 python3 tools/s81_dv/layer_prog/lower_bk.py gen --fixtures ../fx --job topk_final --indexed13 --out "$B/indexed13_$mut" --mutant "$mut"
done
export VL_EXTRA=-DOT_S81PH_SEL_INDEXED13
set +e
bash tools/s81_dv/layer_prog/bk/run_bk_layer.sh ../build "$B/legacy" "$B/indexed13" "$B/indexed13_corrupt" "$B/indexed13_early"
rc=$?
set -e
python3 - <<'PY'
import json
from pathlib import Path
b=Path('../bench')
r={d.name:json.loads((d/'check_result.json').read_text()) for d in b.iterdir() if (d/'check_result.json').exists()}
print('SUITE',r)
assert len(r)==4 and r['legacy']['pass_'] and r['indexed13']['pass_'] and not r['indexed13_corrupt']['pass_'] and not r['indexed13_early']['pass_']
PY
