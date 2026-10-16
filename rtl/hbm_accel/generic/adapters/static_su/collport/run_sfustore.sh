#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../../../../../.."
OUT=${OUT:?set OUT to a scratch directory}; mkdir -p "$OUT"
S=rtl/hbm_accel/generic/adapters/static_su
SRC=("$S/collport/tb_hbm_su_sfustore.sv" "$S/collport/ot_hbm_su_static_sfustore.sv" "$S/data_store/ot_hbm_su_static_pinned_bank.sv" "$S/data_store/ot_hbm_su_static_data_store.sv" physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
sha256sum "${SRC[@]}" > "$OUT/source.sha256"
for m in 0 1 2; do
  iverilog -g2012 -s tb_hbm_su_sfustore -Ptb_hbm_su_sfustore.MUT="$m" -o "$OUT/mut$m.vvp" "${SRC[@]}" > "$OUT/build$m.log" 2>&1
  rc=0; vvp "$OUT/mut$m.vvp" > "$OUT/mut$m.log" 2>&1 || rc=$?
  if [ "$m" = 0 ]; then test "$rc" = 0; else test "$rc" != 0; fi
done
printf 'SFUSTORE_GATE PASS\n'
