#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
V=$(command -v verilator)
"$V" --version | /bin/grep -q "Verilator 5.050"
"$V" --binary --timing -j 4 -Wno-fatal --x-initial unique --x-assign unique +define+OT_MEM_NO_INIT --top-module protocol_tb --Mdir obj_protocol native/ot_sram_1r1w_32x64_m1.v candidate_variants.sv controller_vehicle.sv reference_vehicle.sv protocol_tb.sv >protocol_build.log 2>&1
for seed in 1 17 29 113 787 1009 32003 65521; do
 obj_protocol/Vprotocol_tb +verilator+rand+reset+2 +verilator+seed+"$seed" >"protocol_seed${seed}.log" 2>&1
 /bin/grep -q QMEM8_PROTOCOL_PASS "protocol_seed${seed}.log"
done
set +e
obj_protocol/Vprotocol_tb +early=1 +verilator+rand+reset+2 +verilator+seed+17 >early_go.log 2>&1
rc=$?
set -e
[ "$rc" -ne 0 ]
/bin/grep -q EARLY_GO_FAULT_OBSERVED early_go.log
echo QMEM8_PROTOCOL_SUITE_PASS
