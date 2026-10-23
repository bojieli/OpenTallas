#!/bin/bash
set -eu
O=${1:?outdir};mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
S="rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/dsrom_sys/s81_dv/ot_s81dv_fp_n32.sv rtl/dsrom_sys/s81_dv/ot_s81dv_finish_sram.sv"
"$V" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -DOT_S81DV_XFIN_N10 --top-module fp_tb --Mdir "$O/obj" --build-jobs 4 $S tools/s81_slice/xfin_collector_n9_1021/fp_n8_reference.sv tools/s81_slice/xfin_collector_n9_1021/fp_tb.sv > "$O/build.log" 2>&1
"$O/obj/Vfp_tb" > "$O/positive.log" 2>&1
cat "$O/positive.log"
set +e
"$O/obj/Vfp_tb" +MUTANT > "$O/mutant.log" 2>&1
rc=$?
set -e
[ "$rc" -ne 0 ] && grep -q FP_N10_MISMATCH "$O/mutant.log"
echo FP_N10_CAUSAL_MUTANT_CAUGHT
