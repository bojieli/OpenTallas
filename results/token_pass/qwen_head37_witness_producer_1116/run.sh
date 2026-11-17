#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
VL=$HOME/.local/opentallas-tools/bin/verilator
/usr/bin/time -v -o build.time "$VL" --binary --timing -O0 -finline -j 1 --output-groups 16 --x-assign 0 --x-initial 0 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -CFLAGS '-O0 -w -fno-var-tracking' -f source.f --top-module tb_native_trace --Mdir obj > build.log 2>&1
/usr/bin/time -v -o run.time ./obj/Vtb_native_trace +OT_ROM_DIR=rom +HEAD37_WITNESS_TRACE=actual.trace > run.log 2>&1
grep -q NATIVE_CALREG1_OBSERVER_TRACE_COMPONENT_PASS48 run.log
./obj/Vtb_native_trace +OT_ROM_DIR=rom +HEAD37_WITNESS_TRACE=wronguser.trace +MUT_USER > wronguser.log 2>&1
grep -q NATIVE_OBSERVER_USER_MUTANT_CAUGHT wronguser.log
./obj/Vtb_native_trace +OT_ROM_DIR=rom +HEAD37_WITNESS_TRACE=missing.trace +DROP_OBS > missing.log 2>&1
echo PASS_TRACE_BOOTSTRAP_COMPONENT_ONLY
