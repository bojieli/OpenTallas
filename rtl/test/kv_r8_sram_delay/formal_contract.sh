#!/bin/bash
set -euo pipefail
O=$1
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$ROOT"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
mkdir -p "$O"
for cfg in production full_domain; do
 params=''
 [ "$cfg" != full_domain ] || params='chparam -set BASE 0 -set DMAX 32 -set CW 6 formal_domain;'
 yosys -Q -T -p "read_verilog -formal -sv -D SYNTHESIS rtl/common/ot_dp_dly_cnt_sram.sv rtl/test/kv_r8_sram_delay/macro_contract.sv rtl/test/kv_r8_sram_delay/formal_domain.sv; $params setattr -mod -unset keep_hierarchy; prep -top formal_domain -flatten; setattr -mod -unset keep_hierarchy; setattr -unset keep_hierarchy; flatten; memory_map; opt; select -module formal_domain; async2sync; chformal -lower; sat -show-ports -show age -show depth -show q -show gold -dump_json $O/${cfg}_cex.json -seq 36 -prove-asserts -verify -set-assumes -set-def-inputs -set-init-def; sat -tempinduct -seq 36 -maxsteps 40 -prove-asserts -verify -set-assumes -set-def-inputs -set-init-def" > "$O/$cfg.log" 2>&1
 echo "PROVED $cfg all static strap values and all initial binary pointer/memory states" >> "$O/result.txt"
done
