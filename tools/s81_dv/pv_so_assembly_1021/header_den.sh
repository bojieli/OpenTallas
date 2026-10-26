#!/usr/bin/env bash
set -euo pipefail
O=${1:?};mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing -j 4 -Wno-fatal -Wno-WIDTH --top-module tb_pv_so_ingress -GHEADER_DEN=1 -Mdir "$O/obj" rtl/dsrom_sys/s81_dv/pv_so/dsdv_pv_so_ingress.sv rtl/dsrom_sys/s81_ctrl/ot_s81_svc_job.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.v tools/s81_dv/pv_so_assembly_1021/tb_pv_so_ingress.sv > "$O/build.log" 2>&1
for m in 0 3 8;do "$O/obj/Vtb_pv_so_ingress" +mut=$m > "$O/run$m.log" 2>&1;head -3 "$O/run$m.log";done
