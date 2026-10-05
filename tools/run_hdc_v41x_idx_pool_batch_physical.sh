#!/usr/bin/env bash
# Route the adopted correctness-rate pooled indexer batch (G=4, M=2, IH=32).
# Usage: tools/run_hdc_v41x_idx_pool_batch_physical.sh synth,sta|pnr OUTPUT
set -euo pipefail
cd "$(dirname "$0")/.."
stages=${1:?stages}
out=${2:?output}
args=()
# The boundary producer and query loader launch from adjacent registered tiles.
# This gate measures internal register-to-register timing; boundary paths need
# a later integrated route with their actual launch clocks and wire delays.
for port in rst_n cmd_v cmd_nkeys b_valid b_kv b_ref b_keep b_key w_v w_head w_w w_qsc rd_x; do
    args+=(--false-path-from "$port")
done
exec python3 tools/run_abi3_physical.py \
    --view asap7 --top ot_hdc_v41x_idx_pool_batch \
    --source rtl/hdc/v41x/ot_hdc_v41x_idx_pool_batch.sv \
    --source rtl/hdc/v41x/ot_hdc_v41x_idx_pool_finish.sv \
    --source rtl/hdc/v41x/ot_hdc_v41x_idx_pcol.sv \
    --source rtl/hdc/v41x/ot_hdc_v41x_idx_hsum.sv \
    --source rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv \
    --source rtl/hdc/v41x/ot_hdc_v41x_wgt_tile.sv \
    --source rtl/hdc/v41x/ot_hdc_v41x_wgt_red.sv \
    --source rtl/hdc/v41x/ot_hdc_v41x_wgt_mac.sv \
    --source rtl/hdc/v41x/ot_hdc_v41x_wgt_bdot.sv \
    --source rtl/hdc/ot_hdc_delay.sv \
    --source rtl/hdc/ot_hdc_fastfp.sv \
    --clock-period-ns 2.0 --io-delay-fraction 0 \
    --purpose characterization --core-utilization 35 \
    --stages "$stages" --output "$out" "${args[@]}"
