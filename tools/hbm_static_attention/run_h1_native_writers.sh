#!/bin/bash
set -euo pipefail
out=$1;mkdir -p "$out"
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
common=(rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
for kind in qk pv;do
 files=(rtl/hdc/v41x/static/ot_hbm_attn_${kind}_native_output_h1.sv)
 if [ "$kind" = qk ];then files+=(rtl/hdc/v41x/static/ot_hbm_attn_qk_score_serializer.sv);else files+=(rtl/hdc/v41x/static/ot_hbm_attn_pv_serializer_local.sv rtl/hdc/v41x/static/ot_hbm_attn_pv_bank_gather_registered.sv rtl/hdc/v41x/static/ot_hbm_attn_pv_serializer_local_banked.sv);fi
 "$vl" --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_hbm_attn_${kind}_native_output_h1 --Mdir "$out/${kind}_obj" -o sim "${files[@]}" "${common[@]}" rtl/test/hbm_accel/generic/tb_hbm_attn_${kind}_native_output_h1.sv > "$out/${kind}_build.log" 2>&1
 if [ "$kind" = qk ];then cases='0 1 2 3 4 5 6';else cases='0 1 2 3 4';fi
 for m in $cases;do
  set +e;"$out/${kind}_obj/sim" +MUT=$m > "$out/${kind}_m$m.log" 2>&1;rc=$?;set -e;echo "$rc" > "$out/${kind}_m$m.rc"
  if [ "$m" = 0 ] || [ "$m" = 3 ] || { [ "$kind" = qk ] && { [ "$m" = 1 ] || [ "$m" = 2 ]; }; };then grep -q "PASS .*NATIVE" "$out/${kind}_m$m.log";else grep -qE 'NATIVE (actualbank fault|readback mismatch)' "$out/${kind}_m$m.log";fi
 done
done
echo 'PASS H1 activehead-only SC/PV actualSID0 7b2 bank exclusiveRG0WG0, inactiveflags ignored, actualcommit retirement/epochs; actualarithmetic producer/NEtransport and wholekernel slotgrant open' > "$out/gate"
