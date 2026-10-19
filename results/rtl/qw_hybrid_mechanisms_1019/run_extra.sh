#!/bin/bash
set -euo pipefail
for seed in 17 733 65537; do
 ./obj/Vtb +verilator+seed+$seed > baseline_seed_$seed.log 2>&1
 grep 'PASS fullW10' baseline_seed_$seed.log
done
python3 mutants.py
verilator --binary --timing --top-module tb -Wno-fatal -DOT_MEM_NO_INIT --x-initial unique --x-assign unique -j 8 --Mdir obj_K tb.sv mut_K.sv ot_sram_1r1w2c_32x64_m1.v > build_K.log 2>&1
set +e
./obj_K/Vtb > fail_K.log 2>&1
status=$?
set -e
if [ "$status" = 0 ]; then echo 'HOLLOW K mutant'; exit 1; fi
grep -E 'FF_IDENTITY|SRAM_IDENTITY' fail_K.log
echo "EXPECTED_FAIL K status=$status"
