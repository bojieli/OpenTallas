#!/bin/bash
set -euo pipefail
out=${1:?}
bash rtl/test/hbm_idx_static/run_col8_reset3.sh "$out/pos" 0
set +e
bash rtl/test/hbm_idx_static/run_col8_reset3.sh "$out/mut" 1
rc=$?
set -e
[ "$rc" -ne 0 ]
grep -q COL8_RESET3_FAIL "$out/mut/run.log"
echo COL8_RESET3_PAIR_PASS
