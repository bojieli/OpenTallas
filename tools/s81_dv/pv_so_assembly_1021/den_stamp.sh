#!/usr/bin/env bash
set -euo pipefail
O=${1:?};mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing -Irtl/dsrom_sys/s81_dv/svc_rs -j 4 -Wno-fatal -Wno-WIDTH --top-module tb_pv_den_stamp -Mdir "$O/obj" rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_rs.sv tools/s81_dv/pv_so_assembly_1021/tb_pv_den_stamp.sv > "$O/build.log" 2>&1
"$O/obj/Vtb_pv_den_stamp" > "$O/run.log" 2>&1
grep '^DEN_STAMP_PASS' "$O/run.log"
