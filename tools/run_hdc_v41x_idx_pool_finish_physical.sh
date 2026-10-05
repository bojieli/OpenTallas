#!/usr/bin/env bash
# Route the adopted pooled-index score collector and head sum (G=4,M=2,IH=32).
# Usage: tools/run_hdc_v41x_idx_pool_finish_physical.sh synth,sta|pnr OUTPUT [PERIOD_NS] [NICKNAME_TAG] [EXTRA_DRIVER_ARGS...]
set -euo pipefail
cd "$(dirname "$0")/.."
stages=${1:?stages}
out=${2:?output}
period=${3:-2.0}
args=()
if [[ ${4:-} ]]; then args+=(--nickname-tag "$4"); fi
extra=("${@:5}")
for port in rst_n m_v m_keep m_ref w_v w_head w_w w_qsc p_v p_smask p_ys p_fs p_mask p_y p_f; do
    args+=(--false-path-from "$port")
done
exec python3 tools/run_abi3_physical.py \
    --view asap7 --top ot_hdc_v41x_idx_pool_finish \
    --source rtl/hdc/v41x/ot_hdc_v41x_idx_pool_finish.sv \
    --source rtl/hdc/v41x/ot_hdc_v41x_idx_pcol.sv \
    --source rtl/hdc/v41x/ot_hdc_v41x_idx_hsum.sv \
    --source rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv \
    --source rtl/hdc/ot_hdc_fastfp.sv \
    --source rtl/hdc/ot_hdc_delay.sv \
    --clock-period-ns "$period" --io-delay-fraction 0 \
    --purpose characterization --core-utilization 35 \
    --stages "$stages" --output "$out" "${args[@]}" "${extra[@]}"
