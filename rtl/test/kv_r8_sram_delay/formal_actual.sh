#!/bin/bash
set -euo pipefail
O=$1
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$ROOT"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
mkdir -p "$O"
# Primary, unmodified memory RTL. No array initialization, no pointer initial.
# Preserve this prepared IL to resume SAT without re-expanding task-based memory.
yosys -Q -T -p "read_verilog -formal -sv -D SYNTHESIS -D OT_MEM_NO_INIT rtl/common/ot_dp_dly_cnt_sram.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.v rtl/test/kv_r8_sram_delay/formal_domain.sv; prep -top formal_domain -flatten; setattr -mod -unset keep_hierarchy; setattr -unset keep_hierarchy; flatten; memory_map; opt; select -module formal_domain; write_rtlil $O/prepared.il" > "$O/prepare.log" 2>&1
yosys -Q -T -p "read_rtlil $O/prepared.il; hierarchy -top formal_domain; select -module formal_domain; async2sync; chformal -lower; opt; sat -seq 36 -prove-asserts -verify -set-assumes -set-def-inputs -set-init-def" > "$O/bmc.log" 2>&1
echo 'PASS actual macro binary-state BMC36: static strap0..31 (above24 clamp), arbitrary binary pointer/memory/data' > "$O/result.txt"
