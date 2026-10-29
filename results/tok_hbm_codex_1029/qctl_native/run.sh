#!/bin/bash
set -euo pipefail
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --binary --timing --build-jobs 2 -j 2 -Wno-fatal -Wno-lint -Wno-style --top-module tb_qctl_native --Mdir obj -o tb *.sv *.v >build.log 2>&1
./obj/tb >run.log 2>&1
grep QCTL_PASS run.log
for mut in DROP_PRE BYPASS_GUARD WRONG_CLEAR;do
 if ./obj/tb +"$mut" >"mut_$mut.log" 2>&1;then echo "MUTANT_SURVIVED $mut";exit 1;fi
 grep QCTL_FAIL "mut_$mut.log"
done
