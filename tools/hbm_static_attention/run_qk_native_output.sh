#!/bin/bash
set -euo pipefail
out=$1;mkdir -p "$out"
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$vl" --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_hbm_attn_qk_native_output --Mdir "$out/obj" -o sim \
 rtl/hdc/v41x/static/ot_hbm_attn_qk_score_serializer.sv rtl/hdc/v41x/static/ot_hbm_attn_qk_native_output.sv \
 rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v \
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
 rtl/test/hbm_accel/generic/tb_hbm_attn_qk_native_output.sv > "$out/build.log" 2>&1
for m in 0 3 4 5 6;do
 set +e;"$out/obj/sim" +MUT=$m > "$out/m$m.log" 2>&1;rc=$?;set -e;echo "$rc" > "$out/m$m.rc"
 if [ "$m" = 0 ] || [ "$m" = 3 ];then grep -q 'PASS QK_NATIVE' "$out/m$m.log";else grep -qE 'QK_NATIVE (actualbank fault|readback mismatch)' "$out/m$m.log";fi
done
echo 'PASS actualQKscorestore→NE_WG1 currentbank readback; source arithmetic/SFU/CP binding OPEN' > "$out/gate"
