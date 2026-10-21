#!/usr/bin/env bash
set -euo pipefail
O=${1:?freshoutput};mkdir -p "$O"
V=verilator;[ ! -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ]||V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing -O1 -Wno-fatal -Wno-WIDTH --top-module tb_egress -Mdir "$O/obj" rtl/lib/ot_reset_sync.sv rtl/dsrom_sys/s81_dv/hostb/dsdv_hostb_head_egress.sv tools/s81_dv/hostb_1021/tb_egress.sv --build-jobs 4 >"$O/build.log" 2>&1
for m in 0 2 3 4;do "$O/obj/Vtb_egress" +MODE=$m >"$O/bench$m.log" 2>&1;cat "$O/bench$m.log";done
