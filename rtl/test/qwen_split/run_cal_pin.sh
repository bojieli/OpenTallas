#!/bin/bash
set -euo pipefail
out=$(realpath -m "$1");mut=${2:-0}
mkdir -p "$out"
src=rtl/qwen_sys/d2d_static_20261015
sha256sum "$src"/{qkd_d2d_cal_seq_pin.sv,ot_qwen_d2d_cal_seq.sv,ot_qwen_d2d_cal_seq_dies.sv,d2d_cal_image.svh} rtl/test/qwen_split/tb_qkd_cal_pin.sv > "$out/source.sha256"
iverilog -g2012 -I"$src" -s tb_qkd_cal_pin -Ptb_qkd_cal_pin.MUT="$mut" -o "$out/test.vvp" "$src/qkd_d2d_cal_seq_pin.sv" "$src/ot_qwen_d2d_cal_seq.sv" "$src/ot_qwen_d2d_cal_seq_dies.sv" rtl/test/qwen_split/tb_qkd_cal_pin.sv > "$out/build.log" 2>&1
vvp -n "$out/test.vvp" > "$out/run.log" 2>&1 || { cat "$out/run.log"; exit 1; }
cat "$out/run.log"
grep -q '^CALPIN_PASS starts74 layers72 token3start1' "$out/run.log"
