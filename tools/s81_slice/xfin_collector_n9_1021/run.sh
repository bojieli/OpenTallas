#!/bin/bash
set -eu
O=${1:?outdir};M=${2:-0};mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing -O1 -Wno-fatal -Wno-WIDTH --top-module tb -GMUT="$M" --Mdir "$O/obj" --build-jobs 4 tools/s81_slice/xfin_collector_n9_1021/tb.sv rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv > "$O/build.log" 2>&1
"$O/obj/Vtb" > "$O/run.log" 2>&1
cat "$O/run.log"
