#!/bin/bash
set -euo pipefail
out=$1;mkdir -p "$out"
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$vl" --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_hbm_attn_pv_serializer_local_registered --Mdir "$out/obj" -o sim \
 rtl/hdc/v41x/static/ot_hbm_attn_pv_serializer_local.sv rtl/hdc/v41x/static/ot_hbm_attn_pv_group_gather_registered.sv rtl/hdc/v41x/static/ot_hbm_attn_pv_serializer_local_registered.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v \
 rtl/test/hbm_accel/generic/tb_hbm_attn_pv_serializer_local_registered.sv > "$out/build.log" 2>&1
for overlap in 0 1;do
 "$out/obj/sim" +MUT=0 +OVERLAP=$overlap > "$out/baseline$overlap.log" 2>&1
 grep -q 'PASS PV_LOCAL_SERIALIZER' "$out/baseline$overlap.log"
done
for m in 1 2 3;do
 set +e;"$out/obj/sim" +MUT=$m +OVERLAP=1 > "$out/m$m.log" 2>&1;rc=$?;set -e;echo "$rc" > "$out/m$m.rc"
 grep -qE 'PV_LOCAL_SERIALIZER (phase fault|data mismatch|flag mismatch)' "$out/m$m.log"
done
echo 'PASS D2048-macro PV component fullshape+concurrentreuse+3negativecases; physical clock/mux/control and native WG1 binding OPEN' > "$out/gate"
