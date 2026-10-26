#!/usr/bin/env bash
# ELEM-CENSUS 2026-10-16: kvsys v1.4.3 regional reset root bench (rtl/test/qwen_split/tb_qkd_rst_region.sv, Q-KVSYS-DIE
# 10-15) for the qkd_rst_region kit.  usage: run_rst_region_bench.sh OUTDIR [MUT]
#   MUT 0: must print RST_REGION_PASS (3 chains 40/150/200 into 3 roots, release exactly host + D + 2 + L, re-assert + HOLD)
#   MUT 1: no ignore window (an unflushed relay value may release a region) -> RST_REGION_FAIL
#   MUT 2: dly strap ignored (release calendar broken)                        -> RST_REGION_FAIL
set -euo pipefail
out=${1:?fresh output directory}; mut=${2:-0}; mkdir -p "$out"
R=$(cd "$(dirname "$0")/../.." && pwd)
iverilog -g2012 -s tb_qkd_rst_region -P tb_qkd_rst_region.MUT=$mut -o "$out/sim.vvp" \
  "$R/rtl/test/qwen_split/tb_qkd_rst_region.sv" "$R/rtl/qwen_sys/split_20261014/qkd_rst_region.sv" > "$out/build.log" 2>&1
vvp -n "$out/sim.vvp" 2>&1 | tee "$out/result.log"
grep -q '^RST_REGION_PASS' "$out/result.log"
