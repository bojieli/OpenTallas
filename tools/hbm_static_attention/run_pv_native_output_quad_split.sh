#!/bin/bash
# Per-quadrant PV drain (D local PV, one attention write group per quadrant VM slice). m0 PASS; m1 payload, m2 wrong WG,
# m4 valid-bit, m5 quadrant-binding swap must FAIL; m3 sticky-flag negative passes with record_fault.
set -euo pipefail
out=$1;mkdir -p "$out"
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$vl" --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_hbm_attn_pv_native_output_quad_split --Mdir "$out/obj" -o sim \
 rtl/hdc/v41x/static/ot_hbm_attn_pv_quad_store_registered.sv rtl/hdc/v41x/static/ot_hbm_attn_pv_bank_gather_binary.sv rtl/hdc/v41x/static/ot_hbm_attn_pv_serializer_quad_split.sv \
 rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v \
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
 rtl/test/hbm_accel/generic/tb_hbm_attn_pv_native_output_quad_split.sv > "$out/build.log" 2>&1
for m in 0 1 2 3 4 5;do
 set +e;"$out/obj/sim" +MUT=$m > "$out/m$m.log" 2>&1;rc=$?;set -e;echo "$rc" > "$out/m$m.rc"
 if [ "$m" = 0 ] || [ "$m" = 3 ];then grep -q 'PASS PV_LOCAL_NATIVE PERQUADRANT' "$out/m$m.log";else [ "$rc" != 0 ] && grep -qE 'PV_LOCAL_NATIVE' "$out/m$m.log";fi
done
grep -h PASS "$out/m0.log"
echo 'PASS per-quadrant PV drain: 4 slices x 8 banks actual VM bank/macro commit+readback, m1/m2/m4/m5 killed, m3 sticky negative' > "$out/gate"
