#!/bin/bash
set -euo pipefail
out=${1:?}
bash rtl/test/hbm_idx_static/run_col8_sram_face.sh "$out/pos" 2
set +e
bash rtl/test/hbm_idx_static/run_col8_sram_face.sh "$out/mut" 3
rc=$?
set -e
if [ "$rc" -eq 0 ];then echo WRONG_OFFSET_NOT_CAUGHT;exit 1;fi
grep -q COL8_FACE_LAND_FAIL "$out/mut/run.log"
echo COL8_FACE_PAIR_PASS
