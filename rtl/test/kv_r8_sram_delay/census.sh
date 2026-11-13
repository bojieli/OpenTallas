#!/bin/bash
set -euo pipefail
O=$1
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$ROOT"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
mkdir -p "$O"
yosys -Q -T -p "read_verilog -lib physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1_bb.v; read_verilog -sv -D SYNTHESIS rtl/common/ot_dp_dly_cnt_sram.sv; chparam -set W 291 -set BASE 0 -set DMAX 24 -set CW 5 ot_dp_dly_cnt_sram; synth -top ot_dp_dly_cnt_sram -flatten -noabc; tee -o $O/generic_cells.json stat -json; write_verilog -noattr $O/generic.v" > "$O/census.log" 2>&1
