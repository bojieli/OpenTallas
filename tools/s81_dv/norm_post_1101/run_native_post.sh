#!/bin/bash
set -euo pipefail
/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing --top-module tb_current_native_leaf --build-jobs 2 -O1 -Wno-fatal -Wno-WIDTH -Wno-PINMISSING -Wno-TIMESCALEMOD --output-split 5000 --output-split-cfuncs 500 -MAKEFLAGS 'OPT_FAST=-O0 OPT_SLOW=-O0' --Mdir obj -f defines.f -f source.f tb_current_native_leaf.sv >build.log 2>&1
set +e
obj/Vtb_current_native_leaf >base.log 2>&1;b=$?
obj/Vtb_current_native_leaf +mut_payload >mut_payload.log 2>&1;p=$?
obj/Vtb_current_native_leaf +mut_posta1 >mut_posta1.log 2>&1;a=$?
printf 'BASE_RC=%d\nPAYLOAD_RC=%d\nPOSTA1_RC=%d\n' "$b" "$p" "$a" >status.txt
cat status.txt
grep -E 'POST_COMMAND|POST_FAULT|NATIVE_POST_' base.log
if [ "$b" -ne 0 ]||[ "$p" -eq 0 ]||[ "$a" -eq 0 ];then exit 1;fi
