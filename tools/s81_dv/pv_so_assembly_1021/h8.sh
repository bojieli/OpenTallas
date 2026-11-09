#!/usr/bin/env bash
set -euo pipefail
out=${1:?out}
mkdir -p "$out"
"$HOME/.local/opentallas-tools/bin/verilator" --binary --timing -j 4 -Wno-fatal --top-module tb_pv_so_h8 -Mdir "$out/obj" \
 rtl/dsrom_sys/s81_dv/pv_so/dsdv_pv_so_ingress_h8.sv rtl/dsrom_sys/s81_dv/pv_so/dsdv_pv_half_join_h8.sv \
 rtl/dsrom_sys/s81_ctrl/ot_s81_svc_job.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.v \
 tools/s81_dv/pv_so_assembly_1021/tb_pv_so_h8.sv > "$out/build.log" 2>&1
for mut in 0 1 2 3 4 5; do
 "$out/obj/Vtb_pv_so_h8" +mut=$mut > "$out/run$mut.log" 2>&1
 if [ "$mut" = 0 ]; then grep -q H8_PVSO_PASS "$out/run$mut.log"; else grep -q H8_PVSO_CAUGHT "$out/run$mut.log"; fi
 grep H8_PVSO_ "$out/run$mut.log"
done
