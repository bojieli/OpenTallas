#!/bin/bash
# Raw negative stage for closure admission: the actual selector FF is bypassed.
set -euo pipefail
: "${OUT:?OUT must name a private build directory}"
bash tools/hgi_unit_tput/run_sfu_side_native6r2a.sh
rows=$(python3 -c 'import json; print(json.load(open("results/rtl/hbm_sfu_native6_1015/manifest.json"))["rows"])')
set +e
"$OUT/obj/Vtb_hbm_su_static_side_native6r2a" +DATA=results/rtl/hbm_sfu_native6_1015 +ROWS="$rows" +MUT_EDGE > "$OUT/raw_negative.log" 2>&1
negative_status=$?
set -e
cat "$OUT/raw_negative.log"
exit "$negative_status"
