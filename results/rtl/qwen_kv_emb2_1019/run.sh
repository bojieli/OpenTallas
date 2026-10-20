#!/bin/bash
# KV-EMB2 bench runner: ./run.sh MUT  (Verilator 5.050, the closure daemon's version)
set -u
M=${1:-0}
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
D=$(cd "$(dirname "$0")" && pwd)
B=$D/build_m$M
rm -rf "$B"; mkdir -p "$B"
"$VL" --version
"$VL" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PINMISSING -Wno-TIMESCALEMOD -Wno-LATCH -Wno-MULTIDRIVEN -Wno-BLKSEQ -Wno-UNOPTFLAT -j 2 \
  -DMUT=$M --top-module tb_qkd_embedding_ctx_start -Mdir "$B" -o tb \
  "$D/src/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v" \
  "$D/src/rtl/qwen_sys/static_embedding_20261014/qkd_embedding_row_tx.sv" \
  "$D/src/rtl/qwen_sys/static_embedding_20261014/qkd_embedding_ctx_start.sv" \
  "$D/src/rtl/qwen_sys/static_embedding_20261014/test/tb_qkd_embedding_ctx_start.sv" > "$B/build.log" 2>&1 || { tail -30 "$B/build.log"; echo "BUILD FAIL"; exit 2; }
"$B/tb"
