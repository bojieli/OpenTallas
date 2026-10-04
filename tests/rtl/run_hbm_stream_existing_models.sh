#!/usr/bin/env bash
# Cross-check of the near-HBM KV stream through the repository's existing HBM timing models.
# Usage: tests/rtl/run_hbm_stream_existing_models.sh -GMODEL=0|1|2 [-GLAYERS=8]
set -euo pipefail
cd "$(dirname "$0")/../.."
VERILATOR="${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}"
run_dir="${RUN_DIR:-$(mktemp -d)}"; mkdir -p "$run_dir"
"$VERILATOR" --binary --timing -Wno-fatal -Wno-WIDTH -j 2 --top-module tb_hbm_stream_existing_models \
  --Mdir "$run_dir/obj" "$@" rtl/hdc/kv/ot_hdc_hbm_model.sv rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv \
  rtl/test/model_ready_hbm_r14/tb_hbm_stream_existing_models.sv > "$run_dir/build.log" 2>&1 || { cat "$run_dir/build.log"; exit 1; }
"$run_dir/obj/Vtb_hbm_stream_existing_models"
