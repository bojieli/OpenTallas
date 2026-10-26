#!/bin/bash
set -euo pipefail
python3 src/results/arch/s81_topk_fifo_safe_1019/extras.py
cd src
export VL_EXTRA="-DOT_S81PH_SEL_INDEXED13 -DOT_S81PH_FIFO_SRAM"
set +e
bash tools/s81_dv/layer_prog/bk/run_bk_layer.sh ../build_sram ../bench_sram/indexed13_ties ../bench_sram/indexed13_identity ../bench_sram/indexed13_zeros ../bench_sram/indexed13_ninf
set -e
python3 - <<'CHECK'
import json
from pathlib import Path
b=Path('../bench_sram');r={d.name:json.loads((d/'check_result.json').read_text()) for d in b.iterdir() if (d/'check_result.json').exists()}
assert len(r)==8,r
for n in ['legacy','indexed13','indexed13_ties','indexed13_zeros','indexed13_ninf']:assert r[n]['pass_'],r[n]
for n in ['indexed13_corrupt','indexed13_early','indexed13_identity']:assert not r[n]['pass_'],r[n]
print('FULL_SRAM_SUITE PASS',r)
CHECK
