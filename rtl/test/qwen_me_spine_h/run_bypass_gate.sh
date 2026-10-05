#!/bin/bash
set -euo pipefail
# Minimum same-adder gate; compile/sim remote only. OUT must be fresh.
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
OUT=$1
mkdir "$OUT"
cd "$ROOT"
iverilog -V >"$OUT/compiler-version.log" 2>&1
iverilog -g2012 -s tb_qwen_me_add_bypass_w12 -o "$OUT/gate.vvp" \
 rtl/test/tb_qwen_me_add_bypass_w12.sv rtl/hdc/ot_qwen_me_add_bypass_w12.sv \
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv \
 rtl/hdc/ot_hdc_fastfp.sv >"$OUT/compile.log" 2>&1
vvp "$OUT/gate.vvp" >"$OUT/runtime.log" 2>&1
sha256sum "$OUT/gate.vvp" >"$OUT/binary.sha256"
