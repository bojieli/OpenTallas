#!/usr/bin/env bash
# Production landing group: DQ=128 matches the native ECTL master's request credit.
# land_epoch_bench.sh OUT [GM [EPOCH [KL [KD]]]]
set -euo pipefail
OUT=$(mkdir -p "$1" && readlink -f "$1")
GM=${2:-0}; EP=${3:-1}; KL=${4:-12}; KD=${5:-12}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
K=rtl/qwen_sys/kv_die_20261009
"$V" --binary --timing -O2 -j "${JOBS:-4}" -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-TIMESCALEMOD \
  --top-module tb_qkd_land_rd_kd -GGM="$GM" -GEPOCH="$EP" -GKL="$KL" -GKD="$KD" -GDQ=128 \
  --Mdir "$OUT/obj" rtl/test/qwen_split/tb_qkd_land_rd_kd.sv "$K/qkd_land_strip.sv" \
  "$K/ot_qkvd_kv_merge.sv" "$K/ot_qkvd_fifo.sv" rtl/hdc/ot_hdc_delay.sv > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_qkd_land_rd_kd" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
grep -q '^PASS qkd_land_rd' "$OUT/run.log" && ! grep -q '^FAIL' "$OUT/run.log"
