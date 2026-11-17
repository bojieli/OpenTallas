#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
VL=$HOME/.local/opentallas-tools/bin/verilator
/usr/bin/time -v -o build.time "$VL" --binary --timing -O0 -finline -j 1 --output-groups 16 --x-assign 0 --x-initial 0 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -CFLAGS '-O0 -w -fno-var-tracking' -I. -f source.f --top-module tb_native_gi_witness --Mdir obj > build.log 2>&1
/usr/bin/time -v -o run.time ./obj/Vtb_native_gi_witness +OT_ROM_DIR=rom +HEAD37_WITNESS_TRACE=actual.trace > run.log 2>&1
grep -q NATIVE_GI_15RECORD_COMPONENT_PASS run.log
for mutant in OLD_DATES DROP_OBS BAD_EPOCH NO_ME_RETIRE; do
 ./obj/Vtb_native_gi_witness +OT_ROM_DIR=rom +HEAD37_WITNESS_TRACE="$mutant.trace" +"$mutant" > "$mutant.log" 2>&1
 grep -q NATIVE_GI_WITNESS_MUTANT_CAUGHT "$mutant.log"
done
./obj/Vtb_native_gi_witness +OT_ROM_DIR=rom +HEAD37_WITNESS_TRACE=NO_STAGE_CLEAR.trace +NO_STAGE_CLEAR > NO_STAGE_CLEAR.log 2>&1
grep -q MISSING_STAGE_CLEAR_CAUGHT_REAL_WARM_BOOT NO_STAGE_CLEAR.log
echo PASS_NATIVE_TT_GI_15RECORD_COMPONENT_WARM
