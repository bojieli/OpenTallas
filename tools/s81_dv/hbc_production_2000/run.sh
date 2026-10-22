#!/usr/bin/env bash
set -euo pipefail
out=${1:?output};mkdir -p "$out"
v="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
"$v" --version >"$out/version.txt"
"$v" --binary --timing -O1 -Wno-fatal -Wno-WIDTH --top-module tb_hostb_source --Mdir "$out/obj" --build-jobs 4 \
 rtl/lib/ot_reset_sync.sv rtl/dsrom_sys/s81_dv/unit/dsdv_static_ks6.sv \
 rtl/dsrom_sys/s81_dv/hostb/dsdv_hostb_landing.sv rtl/dsrom_sys/s81_dv/hostb/dsdv_hostb_source.sv \
 tools/s81_dv/hbc_production_2000/tb_hostb_source.sv >"$out/build.log" 2>&1
for m in 0 1 2 3 4 5;do "$out/obj/Vtb_hostb_source" +MODE="$m" >"$out/mode$m.log" 2>&1;cat "$out/mode$m.log";done
