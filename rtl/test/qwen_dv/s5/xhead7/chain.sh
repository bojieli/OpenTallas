#!/bin/bash
# prepare -> install the constructed netlists into rtl/qwen_dv/s5 -> native census + leaf benches (eq / mut), on the FLEET
set -uo pipefail
O=$1; mkdir -p "$O"
bash rtl/test/qwen_dv/s5/xhead7/prepare.sh "$O/prep" > "$O/prepare.out" 2>&1 || { echo PREPARE_FAIL; tail -20 "$O/prep/construct0.log"; exit 1; }
cp "$O/prep/qfd_dv_s5_xhead_bounded.sv" rtl/qwen_dv/s5/qfd_dv_s5_xhead_bounded.sv
cp "$O/prep/helpers0.sv" rtl/qwen_dv/s5/qfd_dv_s5_xhead_bounded_helpers.sv
cp "$O/prep/qfd_dv_s5_xhead_bounded_mut.sv" rtl/qwen_dv/s5/qfd_dv_s5_xhead_bounded_mut.sv
grep -E 'cells|passes|load' "$O/prep/model0.json" | head -20 || true
bash rtl/test/qwen_dv/s5/xhead7/bench.sh "$O/eq" eq > "$O/eq.out" 2>&1 & ep=$!
bash rtl/test/qwen_dv/s5/xhead7/bench.sh "$O/mut" mut > "$O/mut.out" 2>&1 & mp=$!
wait $ep; wait $mp
tail -8 "$O/eq.out"; tail -8 "$O/mut.out"
echo CHAIN_DONE
