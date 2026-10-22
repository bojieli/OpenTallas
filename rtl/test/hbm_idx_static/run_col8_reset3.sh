#!/bin/bash
set -euo pipefail
out=${1:?};mkdir -p "$out"
"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing -j 2 -O1 -Wno-fatal -DRESET_MUT="${2:-0}" --top-module tb_col8_reset3 --Mdir "$out/obj" rtl/test/hbm_idx_static/tb_col8_reset3.sv rtl/hdc/v41x/ot_hidx_rst_tree_3e_f32.sv rtl/lib/ot_rst_relay_l.sv > "$out/build.log" 2>&1
set +e;"$out/obj/Vtb_col8_reset3" > "$out/run.log" 2>&1;rc=$?;set -e
cat "$out/run.log";exit "$rc"
