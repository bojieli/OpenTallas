#!/bin/bash
set -eu
out=$1; shift
mkdir -p "$out"
F="rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv
rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_add_lat_nr.sv
rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_delay.sv
rtl/hdc/nearhbm/ot_qwen_nearhbm_sfu_p.sv rtl/qwen_sys/kv_die_20261009/qkd_astk_leaves.sv
rtl/qwen_sys/split_20261014/qkd_astk_native_er_service.sv rtl/qwen_sys/split_20261014/qkd_astk_native_stack_s.sv
rtl/test/qwen_kv_die/tb_qkd_astk_native_stack.sv
physical/qkd_astk_strip/macros/ot_sram_1r1w_256x128_m1_r2c2/ot_sram_1r1w_256x128_m1_r2c2.v
physical/qkd_astk_strip/macros/ot_sram_1r1w_64x128_m1_r2c2/ot_sram_1r1w_64x128_m1_r2c2.v"
"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing -j 8 -O1 -CFLAGS -O0 \
  -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH \
  +define+KVD_HEADS=1 +define+KVD_Q_FP32=1 +define+KVD_QK_ONLY=1 \
  --top-module tb_qkd_astk_native_stack --Mdir "$out/obj" "$@" $F > "$out/build.log" 2>&1
set +e
"$out/obj/Vtb_qkd_astk_native_stack" ${ASTK_RUN_ARGS:-} > "$out/run.log" 2>&1
rc=$?
set -e
cat "$out/run.log"
test "$rc" = 0 && grep -q '^PASS mapped_astk' "$out/run.log" && ! grep -Eq '^FAIL|%Fatal|Assertion failed' "$out/run.log"
