#!/usr/bin/env bash
# Route the pooled-index key-image producer. Pass --param NL=16 for the
# adopted MP=2 core; the RTL module default NL=8 is a reduced writer slice.
# Usage: tools/run_hdc_v41x_idx_pool_kwr_physical.sh synth,sta|pnr OUTPUT [PERIOD_NS] [NICKNAME_TAG] [EXTRA_DRIVER_ARGS...]
set -euo pipefail
cd "$(dirname "$0")/.."
stages=${1:?stages}
out=${2:?output}
period=${3:-2.0}
args=()
if [[ ${4:-} ]]; then args+=(--nickname-tag "$4"); fi
extra=("${@:5}")
for port in rst_n cfg_ik_base su_go i_dst i_obase i_orow i_nout i_kdim kv_we kv_waddr kv_wdata w_rdy; do
    args+=(--false-path-from "$port")
done
exec python3 tools/run_abi3_physical.py \
    --view asap7 --top ot_hdc_v41x_idx_pool_kwr \
    --source rtl/hdc/v41x/ot_hdc_v41x_idx_pool_kwr.sv \
    --clock-period-ns "$period" --io-delay-fraction 0 \
    --purpose characterization --core-utilization 35 \
    --stages "$stages" --output "$out" "${args[@]}" "${extra[@]}"
