#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=$(realpath -m "$1"); mut=${2:-0}; mkdir -p "$out"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$VL" --version | tee "$out/version.txt"
S=rtl/hbm_accel/generic/adapters/static_su
"$VL" --binary --timing -j 8 --top-module tb_qcore_r9_lockstep -GMUT="$mut" -Wno-fatal --Mdir "$out/obj" -o vtb \
 "$S/top/ot_hbm_su_static_qcore_r5.sv" "$S/top/ot_hbm_su_static_qcore_r9.sv" "$S/register_file/ot_hbm_su_static_rf.sv" "$S/reduction/ot_hbm_su_reduce_static.sv" "$S/reduction/ot_hbm_su_reduce_static_r32.sv" \
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
 rtl/test/hbm_qcore_physical_1016/tb_qcore_r9_lockstep.sv > "$out/build.log" 2>&1
"$out/obj/vtb" | tee "$out/bench.log"
if [[ "$mut" == 0 ]]; then grep -q "QCORE_RG PASS" "$out/bench.log"; else grep -q "QCORE_RG FAIL" "$out/bench.log"; fi
