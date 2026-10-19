#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
V=/opt/verilator-5.050/bin/verilator
if [ ! -x "$V" ]; then V=$(command -v verilator); fi
"$V" --version | tee version.log
"$V" --version | /bin/grep -q 'Verilator 5.050'
"$V" --binary --timing -j 4 -Wno-fatal --x-initial unique --x-assign unique +define+OT_MEM_NO_INIT --top-module tb --Mdir obj_dir native/ot_sram_1r1w_32x64_m1.v candidate_variants.sv legacy_vehicle.sv reference_vehicle.sv tb.sv >build.log 2>&1
for seed in 1 17 29 113 787 1009 32003 65521; do
 obj_dir/Vtb +mode=0 +verilator+rand+reset+2 +verilator+seed+"$seed" >"positive_seed${seed}.log" 2>&1
 /bin/grep -q QMEM8_PASS "positive_seed${seed}.log"
done
for mode in 1 2 3 4 5; do
 set +e
 obj_dir/Vtb +mode="$mode" +verilator+rand+reset+2 +verilator+seed+17 >"mutant${mode}.log" 2>&1
 rc=$?
 set -e
 if [ "$rc" -eq 0 ]; then echo "MUTANT_SURVIVED $mode"; exit 1; fi
 /bin/grep -q QMEM_DATA_FAIL "mutant${mode}.log"
 echo "MUTANT_REJECTED $mode exit=$rc"
done
echo QMEM8_SUITE_PASS

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
