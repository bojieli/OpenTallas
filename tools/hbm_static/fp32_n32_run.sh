#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=$(realpath -m "$1");lat=${2:-6};mkdir -p "$out"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$VL" --version | tee "$out/version.txt"
"$VL" --binary --timing -j 8 -Wno-fatal --top-module tb_fp32_n32 -GDUT_LAT="$lat" --Mdir "$out/obj" -o vtb \
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_add_n32.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv \
 rtl/test/hbm_qcore_physical_1016/tb_fp32_n32.sv > "$out/build.log" 2>&1
for seed in 1 17 91; do "$out/obj/vtb" +seed=$seed | tee "$out/seed_$seed.log";if [[ "$lat" == 6 ]];then grep -q "FP32_N32 PASS" "$out/seed_$seed.log";else grep -q "FP32_N32 FAIL" "$out/seed_$seed.log";fi;done
