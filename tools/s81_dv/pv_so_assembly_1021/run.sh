#!/usr/bin/env bash
set -euo pipefail
O=${1:?outdir};mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing -j 4 -Wno-fatal -Wno-WIDTH --top-module tb_pv_so_ingress -Mdir "$O/obj" \
 rtl/dsrom_sys/s81_dv/pv_so/dsdv_pv_so_ingress.sv rtl/dsrom_sys/s81_ctrl/ot_s81_svc_job.sv \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.v \
 tools/s81_dv/pv_so_assembly_1021/tb_pv_so_ingress.sv > "$O/build.log" 2>&1
for m in 0 1 2 3 4 5 6 7;do
 "$O/obj/Vtb_pv_so_ingress" +mut=$m > "$O/run$m.log" 2>&1
 if [ "$m" = 0 ];then grep -q '^PVSO_PASS' "$O/run$m.log";else grep -q "^PVSO_CAUGHT mut=$m " "$O/run$m.log";fi
 if [ "$m" != 0 ];then
  case "$m" in 1|5) bit=4;;2|6) bit=32;;3) bit=64;;4) bit=128;;7) bit=256;;esac
  code=$(sed -n 's/^PVSO_CAUGHT.*code=//p' "$O/run$m.log")
  test $((16#$code & bit)) != 0
 fi
 tail -3 "$O/run$m.log"
done
