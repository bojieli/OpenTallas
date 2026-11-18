#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
V=$HOME/.local/opentallas-tools/bin/verilator
/usr/bin/time -v -o build.time "$V" --binary --timing -j 1 -O0 -finline --output-groups 64 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH --x-assign 0 --x-initial 0 -CFLAGS '-O0 -w -fno-var-tracking' --top-module tb -f source.f --Mdir obj >build.log 2>&1
/usr/bin/time -v -o run.time ./obj/Vtb >run.log 2>&1
grep -q KV_MEM44_FINISH_COMPONENT_PASS run.log
for mutant in BAD_REPLY BAD_GAIN;do
 set +e
 ./obj/Vtb +"$mutant" >"${mutant}.log" 2>&1
 rc=$?
 set -e
 test "$rc" != 0
 grep -Eq 'KV_FINISH_PAYLOAD|KV_FINISH_COUNT|KV_FINISH_ADDRESS' "${mutant}.log"
done
echo KV_MEM44_FINISH_MUTANTS_CAUGHT
