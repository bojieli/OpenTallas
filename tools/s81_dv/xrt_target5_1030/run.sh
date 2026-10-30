#!/bin/bash
set -u
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
verilator --binary --timing -O1 -j 2 -Wno-fatal -Wno-WIDTH -Wno-PINMISSING --top-module tb_xrt_target5 --Mdir obj src/ot_rst_relay.sv src/ot_s81sl_xrt.sv tb_xrt_target5.sv >build.log 2>&1
rc=$?;echo BUILD_RC=$rc >>status.txt
if [ "$rc" -ne 0 ];then tail -12 build.log;exit "$rc";fi
obj/Vtb_xrt_target5 >base.log 2>&1
rc=$?;echo BASE_RC=$rc >>status.txt
obj/Vtb_xrt_target5 +bad_payload >payload.log 2>&1
p=$?;echo PAYLOAD_RC=$p >>status.txt
obj/Vtb_xrt_target5 +bad_age >age.log 2>&1
a=$?;echo AGE_RC=$a >>status.txt
cat status.txt
if [ "$rc" -eq 0 ]&&[ "$p" -ne 0 ]&&[ "$a" -ne 0 ];then echo GATE_PASS >>status.txt;else exit 1;fi
