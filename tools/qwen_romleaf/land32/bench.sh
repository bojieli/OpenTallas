#!/bin/bash
set -euo pipefail
mkdir -p proof3
"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --version > proof3/tool_version.txt
"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing -j 8 -O2 -Wno-fatal --top-module tb_land32 -Mdir proof3/obj rtl/hdc/ot_hdc_delay.sv rtl/physical/ot_qw_land4.sv rtl/physical/ot_qw_land4_n32.sv tools/qwen_romleaf/land32/tb_land32.sv > proof3/build.log 2>&1
proof3/obj/Vtb_land32 > proof3/positive.log 2>&1
for mut in 1 2 3; do
 if proof3/obj/Vtb_land32 +MUT="$mut" > "proof3/mut${mut}.log" 2>&1; then exit 1; fi
 grep -q LAND32_FAIL "proof3/mut${mut}.log"
done
