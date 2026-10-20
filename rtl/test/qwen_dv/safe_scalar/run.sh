#!/usr/bin/env bash
set -euo pipefail
work=$1
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
mkdir -p "$work"
python3 rtl/test/qwen_dv/safe_scalar/generate.py
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_scalar --Mdir "$work/obj" rtl/test/qwen_dv/safe_scalar/{legacy,safe,tb_scalar}.sv rtl/hdc/{ot_hdc_fastfp,ot_hdc_fp32_add_lat,ot_hdc_fp32_mul_lat,ot_hdc_prefix,ot_hdc_delay,ot_hdc_sfu,ot_hdc_sfu_q}.sv > "$work/build.log" 2>&1
"$work/obj/Vtb_scalar"
