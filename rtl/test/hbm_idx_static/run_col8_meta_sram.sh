#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
out=$(realpath -m "${1:?}");mkdir -p "$out"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$vl" -DMETA_D="${2:-146}" --binary --timing -j 4 -O1 -Wno-fatal --top-module tb_col8_meta_sram --Mdir "$out/obj" rtl/test/hbm_idx_static/tb_col8_meta_sram.sv rtl/hdc/v41x/ot_hidx_meta_sram146.sv physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v > "$out/build.log" 2>&1
set +e
"$out/obj/Vtb_col8_meta_sram" > "$out/run.log" 2>&1
rc=$?
set -e
cat "$out/run.log"
exit "$rc"
