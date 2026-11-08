#!/bin/bash
set -euo pipefail
OUT=$1;MUT=${2:-0};R=$PWD
mkdir -p "$OUT"
"$HOME/.local/opentallas-tools/bin/verilator" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style --top-module tb_svc_pvq_h8_capture_pad -GMUT="$MUT" --unroll-count 2048 -Mdir "$OUT/obj" -j 1 -CFLAGS -O1 \
 "$R/rtl/dsrom_sys/s81_dv/pv_so/ot_svc_pvq_h8_capture_pad.sv" "$R/results/rtl/svc_pvq_h8_pad_1113/tb_svc_pvq_h8_capture_pad.sv" \
 "$R/results/rtl/s81_svc_memory_fit_1103/ot_t7_pvq_capture_v2.sv" \
 "$R/physical/asap7_memory_macros_v2/ot_sram_1r1w_32x128_m1_r0c0/ot_sram_1r1w_32x128_m1_r0c0.v" > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_svc_pvq_h8_capture_pad" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
