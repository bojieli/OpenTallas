#!/bin/bash
# KVJ-D 2026-10-17: qkd_astk_er_tap lockstep against qkd_astk_native_er_service_w (tb_qkd_astk_er_tap).  er_tap_bench.sh OUT [MUT]
set -euo pipefail
OUT=${1:?output}; MUT=${2:-0}; mkdir -p "$OUT"
verilator --binary --timing -j 2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -GMUT="$MUT" --top-module tb_qkd_astk_er_tap -Mdir "$OUT/obj_$MUT" \
 rtl/test/qwen_static_kv/tb_qkd_astk_er_tap.sv rtl/qwen_sys/split_20261014/qkd_astk_er_tap.sv \
 rtl/qwen_sys/split_20261014/qkd_astk_native_er_service_w.sv > "$OUT/build_$MUT.log" 2>&1
"$OUT/obj_$MUT/Vtb_qkd_astk_er_tap" > "$OUT/run_$MUT.log" 2>&1 || { cat "$OUT/run_$MUT.log"; exit 1; }
cat "$OUT/run_$MUT.log"
