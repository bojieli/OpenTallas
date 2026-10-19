#!/usr/bin/env bash
# HBM-NSFIX 10-18: ot_hbm_idx_xq_node_static bench (iverilog). usage: run_xq_node.sh OUTDIR WI MUT
set -euo pipefail
OUT=${1:?outdir}; WI=${2:?wi}; MUT=${3:-0}
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
mkdir -p "$OUT"
iverilog -g2012 -o "$OUT/sim" -s tb_xq_node -P tb_xq_node.WI=$WI -P tb_xq_node.MUT=$MUT \
  "$ROOT/rtl/test/hbm_idx_static/tb_xq_node.sv" \
  "$ROOT/rtl/hbm_accel/index/quad_1017/ot_hbm_idx_xq_node_static.sv" "$ROOT/rtl/lib/ot_rst_relay.sv"
vvp -n "$OUT/sim" | tee "$OUT/run.log"
grep -q "^IDX_XQ_NODE WI$WI MUT$MUT .* PASS$" "$OUT/run.log"
