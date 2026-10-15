#!/bin/bash
set -euo pipefail
out=$1;mkdir -p "$out"
for mut in 0 1;do
 iverilog -g2012 -s tb_mode_local_consumers -Ptb_mode_local_consumers.DECMUT="$mut" -o "$out/m$mut.vvp" \
 rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv rtl/hdc/v41x/static/ot_hbm_attn_staging_mode_local.sv rtl/hdc/v41x/static/ot_hbm_attn_stage_tile_decode.sv \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
 rtl/test/hbm_staging_geometry/tb_mode_local_consumers.sv > "$out/m$mut.compile.log" 2>&1
 set +e;vvp "$out/m$mut.vvp" > "$out/m$mut.log" 2>&1;rc=$?;set -e;echo "$rc" > "$out/m$mut.rc"
 if [ "$mut" = 0 ];then test "$rc" = 0;grep -q 'PASS mode actual34SRAM' "$out/m$mut.log";else test "$rc" != 0;grep -q 'consumer PV decode mismatch' "$out/m$mut.log";fi
done
echo 'PASS actualmode34 localK/PV RTLconsumers +rawABI/residency/olddata +realFP4scaleDUTmutant' > "$out/gate"
