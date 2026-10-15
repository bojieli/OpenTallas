#!/bin/bash
set -euo pipefail
out=$1;mkdir -p "$out"
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$vl" --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_hbm_attn_p_prefetch --Mdir "$out/obj" -o sim \
 rtl/hdc/v41x/static/ot_hbm_attn_p_prefetch.sv rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v \
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
 rtl/test/hbm_accel/generic/tb_hbm_attn_p_prefetch.sv > "$out/build.log" 2>&1
for m in 0 1 2 3 4;do
 set +e;"$out/obj/sim" +MUT=$m > "$out/m$m.log" 2>&1;rc=$?;set -e;echo "$rc" > "$out/m$m.rc"
 if [ "$m" = 0 ];then grep -q 'PASS P_PREFETCH' "$out/m$m.log";else grep -qE 'P_PREFETCH (source/phase fault|mapped SRAM mismatch)' "$out/m$m.log";fi
done
echo 'PASS fullH16 T128/640 P128mappedSRAM/nativeRG3 realVM +4mutants; fullproducer/CP/physicalbinding OPEN' > "$out/gate"
