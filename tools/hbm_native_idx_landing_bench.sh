#!/bin/bash
set -euo pipefail
out=$(realpath -m "$1");mkdir -p "$out"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
src=(rtl/test/hbm_idx_chunk_el/tb_hbm_idx_landing_fifo_native.sv
 rtl/hbm_accel/index/ot_hbm_idx_landing_fifo_native.sv
 rtl/hbm_accel/index/ot_hbm_idx_landing_store_native.sv
 physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
 physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v)
for mut in 0 1;do
 "$vl" --binary --timing -j 2 -O1 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hbm_idx_landing_fifo_native -GMUT="$mut" --Mdir "$out/obj$mut" "${src[@]}" > "$out/build$mut.log" 2>&1
 set +e
 "$out/obj$mut/Vtb_hbm_idx_landing_fifo_native" > "$out/run$mut.log" 2>&1
 rc=$?
 set -e
 cat "$out/run$mut.log"
 if [ "$mut" = 0 ];then
  [ "$rc" = 0 ] && grep -q 'LANDING_FIFO W1098.*PASS' "$out/run$mut.log" && grep -q 'LANDING_FIFO W609.*PASS' "$out/run$mut.log" && grep -q 'LANDING_OVERFLOW.*PASS' "$out/run$mut.log"
 else
  [ "$rc" != 0 ] && grep -q 'Invented logical capacity' "$out/run$mut.log"
 fi
done
sha256sum "${src[@]}" "$out"/obj*/Vtb_hbm_idx_landing_fifo_native > "$out/source_binary.sha256"
