#!/bin/bash
set -euo pipefail
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
cd literal
verilator --binary --timing --top-module tb -Wno-fatal -j 1 --Mdir obj cuts.sv tb.sv > build.log 2>&1
./obj/Vtb > run.log 2>&1
cd ../native
verilator --binary --timing --top-module tb -Wno-fatal -j 1 --Mdir obj native.sv tb.sv > build.log 2>&1
./obj/Vtb > run.log 2>&1
for mutant in MUT_NO_RELOC MUT_PAYLOAD MUT_BEAT; do
 if ./obj/Vtb +"$mutant" > "$mutant.log" 2>&1; then
  echo "UNCUGHT_MUTANT $mutant";exit 1
 fi
 if ! rg -q ROPE_NATIVE_MISMATCH "$mutant.log"; then
  echo "UNEXPECTED_MUTANT_FAILURE $mutant";exit 1
 fi
done
printf '%s\n' PASS_LITERAL_AND_NATIVE_ROPE > ../status
