#!/bin/bash
set -eu
cd /srv/opentallas-scratch/claude/codex-qw-g5f-capture-1020
mkdir -p out
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$VL" --version > out/version.log
for mode in nominal delay nonsticky; do
 define=; if [ "$mode" = delay ]; then define=-DQFD_CAPTURE_MUT_DELAY; fi
 if [ "$mode" = nonsticky ]; then define=-DQFD_CAPTURE_MUT_NONSTICKY; fi
 "$VL" --binary --timing -Wno-fatal -j 2 --top-module tb --Mdir "out/obj_$mode" $define qfd_fault_capture.sv tb_capture.sv > "out/build_$mode.log" 2>&1
 set +e
 "out/obj_$mode/Vtb" > "out/$mode.log" 2>&1
 result=$?
 set -e
 if [ "$mode" = nominal ]; then grep -q CAPTURE_PASS out/nominal.log; test "$result" = 0
 else grep -q CAPTURE_FAIL "out/$mode.log"; test "$result" != 0; fi
 done
printf 'CAPTURE_COHORT_PASS\n' > out/STATUS
