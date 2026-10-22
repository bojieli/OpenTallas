#!/usr/bin/env bash
set -euo pipefail
O=${1:?};mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing -j 4 -Wno-fatal -Wno-WIDTH --top-module tb_pv_half_join -Mdir "$O/obj" rtl/dsrom_sys/s81_dv/pv_so/dsdv_pv_half_join.sv tools/s81_dv/pv_so_assembly_1021/tb_pv_half_join.sv > "$O/build.log" 2>&1
for m in 0 1 2 3;do "$O/obj/Vtb_pv_half_join" +mut=$m > "$O/run$m.log" 2>&1;tail -2 "$O/run$m.log";done
