#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
mut=${1:-0};out=${2:?output directory};mkdir -p "$out"
iverilog -g2012 -Ptb_qcore_native.MUT="$mut" -s tb_qcore_native -o "$out/bench" rtl/test/hbm_qcore_physical_1016/tb_qcore_native.sv rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_static_qcore.sv rtl/hbm_accel/generic/adapters/static_su/register_file/ot_hbm_su_static_rf.sv rtl/hbm_accel/generic/adapters/static_su/reduction/ot_hbm_su_reduce_static.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
vvp -n "$out/bench" | tee "$out/bench.log"
grep -q 'QCORE_NATIVE PASS' "$out/bench.log"
