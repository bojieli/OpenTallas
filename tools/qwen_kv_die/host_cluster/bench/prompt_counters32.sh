#!/bin/bash
set -eu
OUT=${1:-out_cn32};mkdir -p "$OUT"
verilator --version
for mode in pass mutant;do
 defs=();[ "$mode" != mutant ]||defs=(-DOT_HKV_CNT_LA_MUTANT)
 verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style "${defs[@]}" --top-module tb_hkv_cnt_la32 -Mdir "$OUT/$mode" rtl/test/qwen_host/tb_hkv_cnt_la32.sv rtl/qwen_sys/host_cluster_20261017/prompt_pd/ot_hkv_cnt_la.sv >"$OUT/$mode.build.log" 2>&1
 "$OUT/$mode/Vtb_hkv_cnt_la32" >"$OUT/$mode.log" 2>&1
 cat "$OUT/$mode.log"
done
grep -q 'HKV_CNT_LA PASS' "$OUT/pass.log"
grep -q 'HKV_CNT_LA FAIL' "$OUT/mutant.log"
grep -Eq 'mism32=[1-9][0-9]*' "$OUT/mutant.log"
echo 'PROMPT_CN32_SUITE PASS production32/16 200000cycles causalcarrymutant'
