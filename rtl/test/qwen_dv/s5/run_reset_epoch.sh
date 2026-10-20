#!/bin/bash
set -euo pipefail
O=$1;M=${2:-0};mkdir -p "$O"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version
"$V" --binary -j 2 -O1 -Wno-fatal -Wno-lint -Wno-style --top-module tb_s5_reset_epoch -GMUT="$M" rtl/common/landed_parent/ot_pl_land.sv rtl/test/qwen_dv/s5/tb_s5_reset_epoch.sv -Mdir "$O/obj" > "$O/build.log" 2>&1
exec "$O/obj/Vtb_s5_reset_epoch"
