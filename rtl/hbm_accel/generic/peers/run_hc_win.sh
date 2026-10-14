#!/usr/bin/env bash
set -euo pipefail
root_dir=$(cd "$(dirname "$0")/../../../.." && pwd)
out_dir=$(realpath -m "$1");mkdir -p "$out_dir";cd "$root_dir"
verilator_bin=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$verilator_bin" --binary --timing -DOT_WW_MACRO -O1 -j 8 -Wno-fatal -Wno-WIDTH ${XDEF:-} --top-module tb_hgi_hc_win -Mdir "$out_dir/obj" \
 rtl/lib/ot_rst_relay.sv rtl/hdc/hbm/ot_hdc_v41x_weight_window.sv \
 rtl/hbm_accel/generic/peers/ot_hgi_hc_win.sv rtl/hbm_accel/generic/peers/tb_hgi_hc_win.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v > "$out_dir/build.log" 2>&1
"$out_dir/obj/Vtb_hgi_hc_win" > "$out_dir/run.log" 2>&1
if ! grep -q '^HC_WIN PASS$' "$out_dir/run.log"; then cat "$out_dir/run.log";exit 1;fi
cat "$out_dir/run.log"
