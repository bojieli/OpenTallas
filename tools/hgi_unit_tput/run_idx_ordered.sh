#!/bin/bash
set -euo pipefail
out=$(realpath -m "$1")
mu=${2:-0}
mkdir -p "$out"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
[ -x "$V" ] || V=verilator
"$V" --binary --timing -O2 -j 4 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD \
 --top-module tb_hbm_idx_ordered_candidate -GMUT="$mu" -Mdir "$out/obj" \
 rtl/test/hbm_accel/tb_hbm_idx_ordered_candidate.sv \
 rtl/hbm_accel/index/ot_hbm_idx_ordered_candidate.sv \
 rtl/hdc/v41x/ot_hdc_v41x_sel_cand.sv rtl/link/ot_fifo_sram_fwft.sv \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v \
 > "$out/build.log" 2>&1 || { tail -30 "$out/build.log"; echo 'ORDERED BUILD FAILED'; exit 2; }
"$out/obj/Vtb_hbm_idx_ordered_candidate" > "$out/run.log" 2>&1
tail -2 "$out/run.log"
grep -q "ORDERED MUT=$mu .* PASS" "$out/run.log"
