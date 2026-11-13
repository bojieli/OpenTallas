#!/bin/bash
set -euo pipefail
O=$1
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$ROOT"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
mkdir -p "$O"
macro=physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.v
for variant in nominal age_mut count_mut; do
 flags=()
 [ "$variant" != age_mut ] || flags+=(-DOT_DP_DLY_SRAM_AGE_MUT)
 [ "$variant" != count_mut ] || flags+=(-DOT_DP_DLY_SRAM_COUNT_TRUNC_MUT)
 verilator --binary --timing --x-initial unique --x-assign unique -j 4 -Wno-fatal -Werror-WIDTH -Werror-SELRANGE --top-module tb \
  -DOT_MEM_NO_INIT "${flags[@]}" --Mdir "$O/obj_$variant" \
  rtl/common/ot_dp_dly_cnt_sram.sv "$macro" rtl/test/kv_r8_sram_delay/tb.sv > "$O/build_$variant.log" 2>&1
 for seed in 1 17 93; do
  set +e
  "$O/obj_$variant/Vtb" +verilator+seed+$seed +verilator+rand+reset+2 > "$O/${variant}_seed$seed.log" 2>&1
  rc=$?
  set -e
  if [ "$variant" = nominal ]; then
   [ "$rc" = 0 ] && grep -q "LOCKSTEP PASS" "$O/${variant}_seed$seed.log" || exit 2
  else
   [ "$rc" != 0 ] && grep -q "MEMORY_DELAY_MISMATCH" "$O/${variant}_seed$seed.log" || exit 3
  fi
 done
done
echo "ALL PASS: nominal3seeds,2mutantscaught3seeds each" | tee "$O/result.txt"
