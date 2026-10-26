#!/bin/bash
set -euo pipefail
work=$1
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
mkdir -p "$work"
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_cfg --Mdir "$work/obj" rtl/test/qwen_dv/safe_scalar_reset/tb_cfg.sv rtl/qwen_dv/qfd_dv_scalar2_csafe.sv rtl/qwen_dv/qfd_dv_ring_delay.sv rtl/qwen_dv/qfd_dv_reset_tree.sv rtl/qwen_dv/qfd_dv_reset_bank.sv rtl/common/landed_parent/ot_pl_land.sv rtl/hdc/{ot_hdc_fastfp,ot_hdc_fp32_add_lat,ot_hdc_fp32_mul_lat,ot_hdc_prefix,ot_hdc_delay,ot_hdc_sfu,ot_hdc_sfu_q}.sv > "$work/build.log" 2>&1
"$work/obj/Vtb_cfg" ${2:-}
