#!/bin/bash
set -euo pipefail
OUT=$1;mkdir -p "$OUT"
verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hkv_cnt_seg -Mdir "$OUT/obj" rtl/test/qwen_host/tb_hkv_cnt_seg.sv rtl/qwen_sys/host_cluster_20261017/prompt_safe5/ot_hkv_cnt_seg.sv >"$OUT/build.log" 2>&1
"$OUT/obj/Vtb_hkv_cnt_seg" | tee "$OUT/run.log"
grep -q 'HKV_CNT_LA PASS' "$OUT/run.log"
