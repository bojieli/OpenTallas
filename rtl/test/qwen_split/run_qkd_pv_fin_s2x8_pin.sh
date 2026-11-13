#!/bin/bash
set -eu
O=${1:?output directory}
O=$(realpath -m "$O")
mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
[ -x "$V" ] || V=verilator
S=rtl/qwen_sys/split_20261014
"$V" --binary --timing -j 8 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH -Wno-MULTIDRIVEN --top-module tb_qkd_pv_fin_s2x8_pin --Mdir "$O/obj" "$S/qkd_pv_fin_s8.sv" "$S/qkd_pv_fin_s8_pin.sv" rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/test/qwen_split/tb_qkd_pv_fin_s2x8_pin.sv > "$O/build.log" 2>&1
for sd in 3 11; do "$O/obj/Vtb_qkd_pv_fin_s2x8_pin" +SEED=$sd +N=60 > "$O/run_$sd.log"; grep "PVFIN_S2X8 PASS" "$O/run_$sd.log"; done
"$O/obj/Vtb_qkd_pv_fin_s2x8_pin" +SEED=3 +N=30 +SHIFT=0 > "$O/negative_shift0.log"
grep "PVFIN_S2X8 FAIL" "$O/negative_shift0.log"
echo PIN_STAGE_PROOF_PASS
