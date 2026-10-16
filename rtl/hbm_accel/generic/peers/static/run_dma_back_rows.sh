#!/usr/bin/env bash
# H-MTP2/sudma: P-row DMA.KVWB_DS (one move227, m = P rows) on the actual static VM->HBM store engine.
# MUT0 must PASS; MUT1 (engine wrong destination) and MUT3 (descriptor VM row stride dropped) must FAIL.
set -eu
cd "$(dirname "$0")"
out=$(realpath -m "${1:-/tmp/hbm-dma-back-rows}")
macro_root=../../../../../physical/asap7_memory_macros
src="ot_hgi_dma_back_static.sv ../../vm/static/ot_vms_bank_static.sv $macro_root/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v $macro_root/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v tb_dma_back_rows.sv"
mkdir -p "$out"
for mut in 0 1 3; do
  iverilog -g2012 -s tb_dma_back_rows -Ptb_dma_back_rows.MUT="$mut" -o "$out/rows-$mut.vvp" $src > "$out/compile-$mut.log" 2>&1
  set +e; vvp "$out/rows-$mut.vvp" > "$out/sim-$mut.log" 2>&1; rc=$?; set -e
  echo "$rc" > "$out/sim-$mut.exit"; grep -E "DMA_ROWS" "$out/sim-$mut.log" || tail -3 "$out/sim-$mut.log"
  if [ "$mut" -eq 0 ]; then test "$rc" -eq 0; else test "$rc" -ne 0; grep -q "DMA_ROWS FAIL" "$out/sim-$mut.log"; fi
  rm -f "$out/rows-$mut.vvp"
done
echo "DMA_ROWS GATE PASS"
