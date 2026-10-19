#!/bin/bash
set -euo pipefail
python3 mutants.py
for kind in slot epoch written enable metadata pending_reset; do
 verilator --binary --timing --top-module tb -Wno-fatal -DOT_MEM_NO_INIT --x-initial unique --x-assign unique -j 8 --Mdir obj_$kind tb.sv mut_$kind.sv ot_sram_1r1w2c_32x64_m1.v > build_$kind.log 2>&1
 set +e
 ./obj_$kind/Vtb > fail_$kind.log 2>&1
 status=$?
 set -e
 if [ "$status" = 0 ]; then echo "HOLLOW mutant $kind"; exit 1; fi
 grep -E 'FF_IDENTITY|SRAM_IDENTITY|HOLLOW|ASYNC_RESET' fail_$kind.log
 echo "EXPECTED_FAIL $kind status=$status"
done
for kind in ALIAS COLLISION; do
 set +e
 ./obj/Vtb +$kind > diagnostic_$kind.log 2>&1
 status=$?
 set -e
 if [ "$status" = 0 ]; then echo "HOLLOW diagnostic $kind"; exit 1; fi
 grep -E 'LIFECYCLE_ALIAS|FORBIDDEN_SAME_ADDRESS_COLLISION' diagnostic_$kind.log
 echo "PRESERVED_REJECTION $kind status=$status"
done
