#!/usr/bin/env bash
# HBM-NSFIX 10-18: ot_hbm_idx_xq_node_static bench. usage: run_xq_node.sh OUTDIR WI MUT
# Runs on Verilator (the closure daemon pins 5.050: ~/.local/opentallas-tools/verilator-5.050) with --binary --timing.
set -euo pipefail
OUT=${1:?outdir}; WI=${2:?wi}; MUT=${3:-0}
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
V550="$HOME/.local/opentallas-tools/verilator-5.050/bin"
[ -x "$V550/verilator" ] && export PATH="$V550:$PATH"
mkdir -p "$OUT"
verilator --version
verilator --binary --timing -j 1 -Wno-fatal -Wno-lint -Wno-style --top-module tb_xq_node \
  -GWI=$WI -GMUT=$MUT --Mdir "$OUT/obj" -o sim \
  "$ROOT/rtl/test/hbm_idx_static/tb_xq_node.sv" \
  "$ROOT/rtl/hbm_accel/index/quad_1017/ot_hbm_idx_xq_node_static.sv" "$ROOT/rtl/lib/ot_rst_relay.sv" > "$OUT/build.log" 2>&1 \
  || { tail -40 "$OUT/build.log"; exit 2; }
"$OUT/obj/sim" | tee "$OUT/run.log"
grep -q "^IDX_XQ_NODE WI$WI MUT$MUT .* PASS$" "$OUT/run.log"
