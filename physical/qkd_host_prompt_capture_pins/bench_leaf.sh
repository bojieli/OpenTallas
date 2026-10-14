#!/usr/bin/env bash
set -euo pipefail
OUT=$1; CASE=$2; mkdir -p "$OUT"; MUT=0
case "$CASE" in exact) ;; data_mut)MUT=1;; latency_mut)MUT=2;; ecc_mut)MUT=3;; *)exit 2;;esac
T=tb_qkd_host_prompt_capture_pins
iverilog -g2012 -s "$T" -P"$T.MUT=$MUT" -o "$OUT/sim" rtl/test/qwen_host/tb_qkd_host_prompt_capture_pins.sv rtl/physical/ot_qkd_host_prompt_capture_pins.sv rtl/physical/ot_qfd_prompt_sram_capture.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v > "$OUT/build.log" 2>&1
set +e
vvp "$OUT/sim" > "$OUT/run.log" 2>&1
rc=$?
set -e
cat "$OUT/run.log"
exit "$rc"
