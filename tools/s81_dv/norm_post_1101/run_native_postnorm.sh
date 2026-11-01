#!/bin/bash
set -euo pipefail
/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing --top-module tb_current_native_leaf --build-jobs 2 -O1 -Wno-fatal -Wno-WIDTH -Wno-PINMISSING -Wno-TIMESCALEMOD --output-split 5000 --output-split-cfuncs 500 -MAKEFLAGS 'OPT_FAST=-O0 OPT_SLOW=-O0' --Mdir obj -f defines.f -f source.f tb_current_native_leaf.sv >build.log 2>&1
set +e
obj/Vtb_current_native_leaf >base.log 2>&1;b=$?
obj/Vtb_current_native_leaf +mut_headgain >mut_headgain.log 2>&1;g=$?
printf 'BASE_RC=%d\nHEADGAIN_RC=%d\n' "$b" "$g" >status.txt
cat status.txt
grep -E 'POSTNORM_|POST_FAULT|POST_TIMING|NATIVE_POSTNORM_' base.log
if [ "$b" -ne 0 ]||[ "$g" -eq 0 ];then exit 1;fi
