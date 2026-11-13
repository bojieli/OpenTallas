#!/bin/bash
set -euo pipefail
O=$1
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$ROOT"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
mkdir -p "$O"
for kind in legal illegal; do
 cfg='-set BASE 0 -set DMAX 24 -set CW 5'
 [ "$kind" != illegal ] || cfg='-set BASE 0 -set DMAX 63 -set CW 6'
 set +e
 yosys -Q -T -p "read_verilog -lib physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1_bb.v; read_verilog -sv -D SYNTHESIS rtl/common/ot_dp_dly_cnt_sram.sv; chparam -set W 291 $cfg ot_dp_dly_cnt_sram; hierarchy -check -top ot_dp_dly_cnt_sram" > "$O/$kind.log" 2>&1
 rc=$?
 set -e
 if [ "$kind" = legal ]; then [ "$rc" = 0 ];
 else [ "$rc" != 0 ] && grep -q 'OT_DP_DLY_CNT_SRAM_REQUIRES_LEGAL_32_WORD_SHAPE' "$O/$kind.log";fi
done
echo 'PASS legalDMAX24/CW5 accepted; illegalDMAX63/CW6 fail-closed underSYNTHESIS' > "$O/result.txt"
