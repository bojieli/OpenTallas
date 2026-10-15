#!/bin/bash
set -euo pipefail
out=$1;mkdir -p "$out"
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$vl" --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_hbm_attn_pv_serializer --Mdir "$out/obj" -o sim \
 rtl/hdc/v41x/static/ot_hbm_attn_pv_serializer.sv physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v \
 rtl/test/hbm_accel/generic/tb_hbm_attn_pv_serializer.sv > "$out/build.log" 2>&1
for m in 0 1 2 3;do
 set +e;"$out/obj/sim" +MUT=$m > "$out/m$m.log" 2>&1;rc=$?;set -e;echo "$rc" > "$out/m$m.rc"
 if [ "$m" = 0 ];then grep -q 'PASS PV_SERIALIZER' "$out/m$m.log";else grep -qE 'PV_SERIALIZER (phase fault|data mismatch|flag mismatch)' "$out/m$m.log";fi
done
"$out/obj/sim" +MUT=0 +OVERLAP=1 > "$out/overlap.log" 2>&1
grep -q 'PASS PV_SERIALIZER.*overlap1' "$out/overlap.log"
echo 'PASS full H16/D512 PV transpose SRAM128/faultFF16384 3records +3 mutants; nativebinding/physicalunqualified' > "$out/gate"
