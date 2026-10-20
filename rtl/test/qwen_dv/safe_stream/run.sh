#!/bin/bash
set -euo pipefail
work=$1;mut=${2:-0}
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
mkdir -p "$work"
python3 rtl/test/qwen_dv/safe_stream/generate.py
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_stream -GMUT="$mut" --Mdir "$work/obj$mut" rtl/test/qwen_dv/safe_stream/{legacy,safe,tb_stream}.sv rtl/qwen_dv/qfd_dv_reset_tree.sv > "$work/build$mut.log" 2>&1
"$work/obj$mut/Vtb_stream"
