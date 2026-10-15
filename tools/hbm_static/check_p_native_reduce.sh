#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=$(realpath -m "$1")
mkdir -p "$out"
python3 tools/hbm_static/make_p_reduce_join_gate.py tools/hbm_static/su_reduce_compile.py "$out/fixture"
iverilog -g2012 -s tb_hbm_p_native_reduce_static -o "$out/sim" \
 rtl/test/hbm_accel/generic/tb_hbm_p_native_reduce_static.sv \
 rtl/hbm_accel/generic/adapters/static_su/reduction/ot_hbm_p_native_reduce_static.sv \
 rtl/hbm_accel/generic/adapters/static_su/reduction/ot_hbm_p_reduce_ingress_static.sv \
 rtl/hbm_accel/generic/adapters/static_su/reduction/ot_hbm_p_scalar_publish_static.sv \
 rtl/hbm_accel/generic/adapters/static_su/reduction/ot_hbm_su_reduce_static.sv \
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
vvp "$out/sim" +DIR="$out/fixture" >"$out/base.log" 2>&1
if vvp "$out/sim" +DIR="$out/fixture" +MUTANT_SOURCE >"$out/mutant.log" 2>&1;then
 echo 'FAIL missing source-index mutant rejection';exit 1
fi
cat "$out/base.log" "$out/mutant.log"
echo 'PASS actual SRAM source-index mutant rejected'
