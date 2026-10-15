#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
out=${1:?output directory}
macro=${SRAM_MODEL:-../../../../../physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v}
if [[ -f ot_sram_1r1w_1024x256_m2_r2c2.v ]];then macro=ot_sram_1r1w_1024x256_m2_r2c2.v;fi
mkdir -p "$out"
for mut in 0 1 2;do
  iverilog -g2012 -s tb_vms_calendar_static -Ptb_vms_calendar_static.MUT="$mut" -o "$out/m$mut" ot_vms_calendar_static.sv "$macro" tb_vms_calendar_static.sv >"$out/m$mut.compile.log" 2>&1
  if vvp "$out/m$mut" >"$out/m$mut.log" 2>&1;then
    [[ "$mut" == 0 ]] || exit 1
  else
    [[ "$mut" != 0 ]] || { cat "$out/m$mut.log";exit 1; }
    grep -q 'CALENDAR ' "$out/m$mut.log"
  fi
  cat "$out/m$mut.log"
done
