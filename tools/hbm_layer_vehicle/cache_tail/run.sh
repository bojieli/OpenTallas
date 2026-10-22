#!/bin/bash
set -euo pipefail
out=${1:?out};mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
mem=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
for m in 0 1 2 3;do
  iverilog -g2012 -s tb_cache_tail -Ptb_cache_tail.MUT="$m" -o "$out/m$m.vvp" "$mem" "$d/ot_hbm_svc_static_sm_packed136.sv" tools/hbm_layer_vehicle/cache_tail/tb_cache_tail.sv
  if vvp "$out/m$m.vvp" > "$out/m$m.log" 2>&1;then
    test "$m" = 0;grep 'CACHE_TAIL_PASS' "$out/m$m.log"
  else
    test "$m" != 0
    case "$m" in 1)grep 'OPEN_REJECT running tail' "$out/m$m.log";;2)grep 'READ_REJECT sticky' "$out/m$m.log";;3)grep 'RETIRE_REJECT sticky' "$out/m$m.log";;esac
  fi
done
