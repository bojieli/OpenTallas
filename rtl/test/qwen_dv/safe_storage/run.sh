#!/usr/bin/env bash
set -euo pipefail
work=$1;mut=${2:-0}
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
mkdir -p "$work"
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_storage -GMUT="$mut" --Mdir "$work/obj$mut" rtl/qwen_dv/qfd_dv_redstn2.sv rtl/test/qwen_dv/safe_storage/{sram_model,tb_storage}.sv > "$work/build$mut.log" 2>&1
"$work/obj$mut/Vtb_storage"
