#!/usr/bin/env bash
set -eu
out=${1:?output directory}; mkdir -p "$out"
for mut in 0 1 2; do
 "${VERILATOR:-verilator}" --binary -j 4 -Wno-fatal --top-module tb_hnx_pl_pad_sram -GMUT=$mut -GOUTREG=${OUTREG:-0} -GINREG=${INREG:-0} \
  rtl/hbm_next/common/{hnx_pl_pad_sram,tb_hnx_pl_pad_sram}.sv \
  physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
  physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v \
  -Mdir "$out/obj$mut" > "$out/build$mut.log" 2>&1
 set +e
 "$out/obj$mut/Vtb_hnx_pl_pad_sram" > "$out/mut$mut.log" 2>&1
 rc=$?
 set -e
 if [ "$mut" = 0 ]; then test "$rc" = 0; grep 'HNXPAD PASS' "$out/mut$mut.log";
 else test "$rc" != 0; grep 'HNXPAD FAIL' "$out/mut$mut.log"; fi
done
