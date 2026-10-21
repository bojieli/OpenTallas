#!/bin/bash
set -euo pipefail
work=$1
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
mkdir -p "$work"
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_bank_width --Mdir "$work/obj" rtl/qwen_dv/qfd_dv_redstn2.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.v rtl/test/qwen_dv/safe_storage/tb_bank_width.sv > "$work/build.log" 2>&1
"$work/obj/Vtb_bank_width"
