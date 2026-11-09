#!/usr/bin/env bash
set -euo pipefail
O=$1;mkdir -p "$O"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$VL" --binary --top-module tb_svc_h8_pfold -Mdir "$O/obj" -j 4 -Wno-fatal -Wno-WIDTH -Werror-SELRANGE -Wno-TIMESCALEMOD rtl/dsrom_sys/s81_dv/svc_rs/test/tb_svc_h8_pfold.sv > "$O/build.log" 2>&1
for m in 0 1;do "$O/obj/Vtb_svc_h8_pfold" +mut=$m > "$O/run_mut$m.log" 2>&1;grep '^H8_PFOLD' "$O/run_mut$m.log";done
grep -q '^H8_PFOLD PASS$' "$O/run_mut0.log"
grep -q '^H8_PFOLD FAIL$' "$O/run_mut1.log"
