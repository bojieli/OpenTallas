#!/usr/bin/env bash
# Near-HBM KV stream bench: ot_hbm_r14_stream_stack against a picosecond HBM3E timing checker.
# Usage: tests/rtl/run_hbm_stream_bw.sh [-GREF_MODE=1] [-GHINT=320] [-GB2B=0] [-GPHASE=0] ...
set -euo pipefail
cd "$(dirname "$0")/../.."
VERILATOR="${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}"
run_dir="${RUN_DIR:-$(mktemp -d)}"; mkdir -p "$run_dir"
"$VERILATOR" --binary --timing -Wno-fatal -Wno-WIDTH -j 2 --top-module tb_hbm_stream_bw \
  --Mdir "$run_dir/obj" "$@" \
  rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv rtl/model_ready_hbm_r14/ot_hbm_r14_stream_stack.sv \
  rtl/test/model_ready_hbm_r14/tb_hbm_stream_bw.sv > "$run_dir/build.log" 2>&1 || { cat "$run_dir/build.log"; exit 1; }
"$run_dir/obj/Vtb_hbm_stream_bw"
