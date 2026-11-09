#!/usr/bin/env bash
set -euo pipefail
out=${1:?out};mkdir -p "$out"
"$HOME/.local/opentallas-tools/bin/verilator" --binary --timing -j 1 -Wno-fatal --top-module tb_pv_so_program_h8 -Mdir "$out/obj" rtl/dsrom_sys/s81_dv/pv_so/dsdv_pv_so_program_h8.sv tools/s81_dv/pv_so_assembly_1021/tb_pv_so_program_h8.sv > "$out/build.log" 2>&1
for m in 0 1 2 3; do
 "$out/obj/Vtb_pv_so_program_h8" +mut=$m > "$out/run$m.log" 2>&1
 if [ "$m" = 0 ]; then grep -q H8_PROGRAM_PASS "$out/run$m.log"; else grep -q H8_PROGRAM_CAUGHT "$out/run$m.log"; fi
 grep H8_PROGRAM_ "$out/run$m.log"
done
