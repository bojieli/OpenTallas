#!/usr/bin/env bash
# Build the dual-clock Verilator bench of ot_ratio_cdc_fifo.  Usage: build_tb.sh OUTDIR [W] [DEPTH] [HOLD]
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
OUT=$1; W=${2:-64}; DEPTH=${3:-4}; HOLD=${4:-2}
mkdir -p "$OUT"
verilator --cc --exe -O3 --x-assign unique --x-initial unique -Wall -Wno-fatal \
  -GW=$W -GDEPTH=$DEPTH -GHOLD=$HOLD --top-module ot_ratio_cdc_fifo \
  "${RTL:-$ROOT/rtl/common/ot_ratio_cdc_fifo.sv}" "$ROOT/rtl/test/two_clock/tb_ratio_cdc_fifo.cpp" \
  -Mdir "$OUT" -o tb > "$OUT/verilate.log" 2>&1
make -s -C "$OUT" -f Vot_ratio_cdc_fifo.mk -j8 > "$OUT/make.log" 2>&1
echo "$OUT/tb"
