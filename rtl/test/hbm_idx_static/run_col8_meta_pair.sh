#!/bin/bash
set -euo pipefail
out=${1:?}
bash rtl/test/hbm_idx_static/run_col8_meta_sram.sh "$out/pos" 146
set +e
bash rtl/test/hbm_idx_static/run_col8_meta_sram.sh "$out/mut" 145
rc=$?
set -e
if [ "$rc" -eq 0 ];then echo META_WRONG_OFFSET_NOT_CAUGHT;exit 1;fi
grep -q COL8_META_SRAM_FAIL "$out/mut/run.log"
echo COL8_META_PAIR_PASS
