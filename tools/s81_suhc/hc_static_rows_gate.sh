#!/usr/bin/env bash
set -euo pipefail
out=$(realpath -m "$1")
mkdir -p "$out"
verilator --binary --timing -j 4 -Wno-fatal -Wno-WIDTH --top-module tb_s81_hc_rows_static --Mdir "$out/obj" \
 rtl/dsrom_sys/s81_suhc/static/ot_s81_hc_rows_static.sv rtl/dsrom_sys/s81_suhc/static/tb_s81_hc_rows_static.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v > "$out/build.log" 2>&1
"$out/obj/Vtb_s81_hc_rows_static" > "$out/pass.log" 2>&1
set +e
"$out/obj/Vtb_s81_hc_rows_static" +MUT_TAG > "$out/mut_tag.log" 2>&1
rc=$?
set -e
if [[ "$rc" == 0 ]] || ! rg -q 'HC_STATIC_ROWS FAIL' "$out/mut_tag.log"; then exit 1; fi
cat "$out/pass.log"
echo "HC_STATIC_ROWS tagmutant rejected rc=$rc"
