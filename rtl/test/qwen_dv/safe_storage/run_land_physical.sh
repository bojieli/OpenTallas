#!/bin/bash
set -euo pipefail
work=$1;mut=${2:-0}
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
mkdir -p "$work"
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_land_physical -GMUT="$mut" --Mdir "$work/obj$mut" rtl/test/qwen_dv/safe_storage/tb_land_physical.sv rtl/common/landed_parent/ot_pl_land.sv rtl/common/landed_parent/ot_pl_land_physical.sv > "$work/build$mut.log" 2>&1
"$work/obj$mut/Vtb_land_physical"
