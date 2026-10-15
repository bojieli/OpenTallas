#!/bin/bash
set -euo pipefail
out=$1;mkdir -p "$out"
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$vl" --binary --timing -O1 -j 4 --x-initial unique -DOT_MEM_NO_INIT -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_hbm_attn_h1_prefetch --Mdir "$out/obj" -o sim \
 rtl/hdc/v41x/static/ot_hbm_attn_query_prefetch_partitioned.sv rtl/hdc/v41x/static/ot_hbm_attn_p_prefetch_fields.sv \
 "${Q_H1_RTL:-rtl/hdc/v41x/static/ot_hbm_attn_query_prefetch_h1.sv}" "${P_H1_RTL:-rtl/hdc/v41x/static/ot_hbm_attn_p_prefetch_h1.sv}" \
 rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v \
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
 rtl/test/hbm_accel/generic/tb_hbm_attn_h1_prefetch.sv > "$out/build.log" 2>&1
for seed in 41 73;do "$out/obj/sim" +verilator+rand+reset+2 +verilator+seed+$seed > "$out/seed$seed.log" 2>&1;grep -q 'PASS H1_PREFETCH' "$out/seed$seed.log";done
set +e;"$out/obj/sim" +MUT=1 +verilator+rand+reset+2 > "$out/grid_mutant.log" 2>&1;rc=$?;set -e;echo "$rc" > "$out/grid_mutant.rc"
if [ "$rc" = 0 ];then echo 'FAIL H1 grid mutant survived';exit 1;fi
grep -q 'H1_PREFETCH actual helper fault' "$out/grid_mutant.log"
echo 'PASS H1 real query/P SRAM zero initialization, actualbank7b2 SID0 exclusiveRG0WG0; source transport and native arithmetic/fullkernel grant open' > "$out/gate"
