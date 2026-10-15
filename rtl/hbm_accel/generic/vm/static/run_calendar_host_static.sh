#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
out=${1:?output directory}
macro=${SRAM_MODEL:-../../../../../physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v}
loader=${LOADER_CP_SOURCE:-../../loader/ot_hgi_loader_cp.sv}
if [[ -f ot_sram_1r1w_1024x256_m2_r2c2.v ]];then macro=ot_sram_1r1w_1024x256_m2_r2c2.v;fi
if [[ -f ot_hgi_loader_cp.sv ]];then loader=ot_hgi_loader_cp.sv;fi
mkdir -p "$out"
for mut in 0 1 2;do
  iverilog -g2012 -s tb_vms_calendar_host_static -Ptb_vms_calendar_host_static.MUT="$mut" -o "$out/m$mut" ot_vms_calendar_host_static.sv ot_static_program_target.sv ot_vms_calendar_static.sv "$loader" "$macro" tb_vms_calendar_host_static.sv >"$out/m$mut.compile.log" 2>&1
  if vvp "$out/m$mut" >"$out/m$mut.log" 2>&1;then
    [[ "$mut" == 0 ]] || exit 1
  else
    [[ "$mut" != 0 ]] || { cat "$out/m$mut.log";exit 1; }
    if [[ "$mut" == 1 ]];then grep -q 'HOST_CALENDAR wrong actual programme q2' "$out/m$mut.log";else grep -q 'HOST_CALENDAR wrong engine target48' "$out/m$mut.log";fi
  fi
  cat "$out/m$mut.log"
done
