#!/bin/bash
set -u
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
verilator --binary --timing -O1 -j 2 -Wno-fatal -Wno-WIDTH -Wno-PINMISSING -Wno-TIMESCALEMOD --top-module tb_entry_reload --Mdir obj -f defines.f -f files.f tb_entry_reload.sv >build.log 2>&1
rc=$?;echo BUILD_RC=$rc >status.txt
if [ "$rc" -ne 0 ];then tail -15 build.log;exit "$rc";fi
obj/Vtb_entry_reload >base.log 2>&1
b=$?;echo BASE_RC=$b >>status.txt
obj/Vtb_entry_reload +bad_mu >bad_mu.log 2>&1
m=$?;echo MU_MUTANT_RC=$m >>status.txt
obj/Vtb_entry_reload +bad_payload >bad_payload.log 2>&1
p=$?;echo PAYLOAD_MUTANT_RC=$p >>status.txt
cat status.txt
if [ "$b" -eq 0 ]&&[ "$m" -ne 0 ]&&[ "$p" -ne 0 ]&&grep -q 'mf8' bad_mu.log;then echo GATE_PASS >>status.txt;else exit 1;fi
