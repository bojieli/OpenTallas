#!/bin/bash
# ASAP7 synthesis / place-and-route of one V4.1x weight-engine tile (block `wgt`).
# Usage: tools/run_hdc_v41x_wgt_route.sh <top> <stages> <output.json> [period_ns] [extra run_abi3_physical args...]
#   <top>: ot_hdc_v41x_wgt_qtile | ot_hdc_v41x_wgt_qtile_m2 | ot_hdc_v41x_wgt_mtile
# Every tile input lands in a register (descriptor stage A, lane P0, credit register) and every output
# leaves a register, so the I/O delay fraction is 0 and the input ports are false-path sources (as the
# as-built ot_hdc_blockdot route): with a zero input delay against the clock tree's insertion every input
# flop is a hold violation that belongs to the neighbour's launch, not to this tile (the first route
# attempt inserted 36,787 hold buffers on the P0 registers and hit RSZ-0060).
set -euo pipefail
top=$1; stages=$2; out=$3; period=${4:-0.9}; shift 4 || shift $#
cd "$(dirname "$0")/.."
fp=()
for p in rst_n d_v d_plg d_nb d_nrows d_wbase d_ind d_eid d_estride d_fp4 d_tag rd_w rd_x o_cr; do
  fp+=(--false-path-from "$p")
done
exec python3 tools/run_abi3_physical.py --view asap7 --top "$top" \
  --source rtl/hdc/v41x/ot_hdc_v41x_wgt_tops.sv --source rtl/hdc/v41x/ot_hdc_v41x_wgt_tile.sv \
  --source rtl/hdc/v41x/ot_hdc_v41x_wgt_red.sv --source rtl/hdc/v41x/ot_hdc_v41x_wgt_mac.sv \
  --source rtl/hdc/v41x/ot_hdc_v41x_wgt_bdot.sv --source rtl/hdc/ot_hdc_delay.sv --source rtl/hdc/ot_hdc_fastfp.sv \
  --clock-period-ns "$period" --io-delay-fraction 0 "${fp[@]}" \
  --stages "$stages" --output "$out" "$@"
