#!/usr/bin/env bash
set -euo pipefail
O=${1:?output directory}; mkdir -p "$O"; O=$(cd "$O" && pwd)
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$VL" --version
"$VL" --binary --timing -j 4 -Wno-fatal -Wno-WIDTH -DBMUL_RTL \
 --top-module tb_svc7_bmul -Mdir "$O/obj" -o sim \
 rtl/hdc/v41x/ot_s81svc7_bmul_graph_input.sv \
 rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv \
 rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv \
 rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv rtl/hdc/ot_hdc_prefix.sv \
 tools/s81_dv/svc_rs/tb_svc7_bmul.sv > "$O/build.log" 2>&1
"$O/obj/sim" > "$O/run.log" 2>&1
tail -n 6 "$O/run.log"
