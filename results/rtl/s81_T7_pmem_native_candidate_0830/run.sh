#!/bin/bash
set -euo pipefail
ulimit -c 0
R=/srv/opentallas-scratch2/claude/codex-ds-t7-pmem-native-0830
cd "$R"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
sha256sum native_memory.sv native_capture.sv sram.v pmem_candidate.sv tb.sv > inputs.sha256
/usr/bin/time -v "$V" --binary --timing -O1 -j 2 --x-assign 0 --x-initial 0 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-lint -Wno-style --top-module tb -Mdir "$R/obj" native_memory.sv native_capture.sv sram.v pmem_candidate.sv tb.sv > build.log 2> build.err
set +e
./obj/Vtb > positive.log 2>&1
rc=$?
set -e
echo "$rc" > positive.rc
[[ "$rc" == 0 ]] && grep -q '^PMEM_NATIVE_PASS ' positive.log
for mutant in 1 2 3; do
 set +e
 ./obj/Vtb +mutant="$mutant" > "mutant_$mutant.log" 2>&1
 rc=$?
 set -e
 echo "$rc" > "mutant_$mutant.rc"
 [[ "$rc" != 0 ]] && grep -q '^PMEM_NATIVE_FAIL ' "mutant_$mutant.log"
done
