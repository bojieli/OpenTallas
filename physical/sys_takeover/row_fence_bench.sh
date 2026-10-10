#!/bin/bash
# sys-takeover 2026-10-09: qfd_row_merge_native_fence exact bench (rtl/test/qwen_system/tb_qfd_row_merge_fence.sv:
# 24 layers x 32 PC head owners, random row-arb grants, KV4-style 400-edge write-ack stall every third layer).
#   row_fence_bench.sh pos|neg1|neg2 OUT     neg1: fence off (MUT=1)   neg2: ACK lane to pc+1 (MUT=2)
set -uo pipefail
mode=$1; W=$2; mkdir -p "$W"
case $mode in pos) M=0;; neg1) M=1;; neg2) M=2;; *) echo "bad mode"; exit 2;; esac
iverilog -g2012 -Ptb_qfd_row_merge_fence.MUT=$M -s tb_qfd_row_merge_fence -o "$W/s.vvp" \
  rtl/qwen_sys/system_20261009/ot_qfd_row_merge_fence.sv rtl/test/qwen_system/tb_qfd_row_merge_fence.sv >"$W/build.log" 2>&1 \
  || { cat "$W/build.log"; echo ROW_FENCE_BENCH_ERROR; exit 2; }
vvp -n "$W/s.vvp" >"$W/run.log" 2>&1; grep -E "PASS|FATAL" "$W/run.log" | head -3
if [[ $mode == pos ]]; then
  grep -q '^PASS_ROW_FENCE' "$W/run.log" && ! grep -q FATAL "$W/run.log" && { echo ROW_FENCE_PASS; exit 0; }
  echo ROW_FENCE_FAIL; exit 1
fi
grep -q FATAL "$W/run.log" && { echo ROW_FENCE_NEG_DETECTED; exit 1; }
echo ROW_FENCE_NEG_MISSED; exit 0
