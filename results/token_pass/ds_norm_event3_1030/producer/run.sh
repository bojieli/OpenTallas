#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
TASK=/srv/opentallas-scratch2/claude/codex-ds-norm-producer-1030
cd "$TASK"
python3 stage.py "$TASK" > stage.log 2>&1
verilator --binary --timing -O1 -j 2 -Wno-fatal -Wno-WIDTH -Wno-PINMISSING --top-module tb_norm_producer --Mdir obj -f defines.f -f source.f tb_norm_producer.sv > build.log 2>&1
set +e
obj/Vtb_norm_producer >base.log 2>&1;b=$?
obj/Vtb_norm_producer +bad_payload >payload.log 2>&1;p=$?
obj/Vtb_norm_producer +bad_age >age.log 2>&1;a=$?
printf 'BASE_RC=%s\nPAYLOAD_RC=%s\nAGE_RC=%s\n' "$b" "$p" "$a" >status.txt
cat status.txt
if [ "$b" -eq 0 ]&&[ "$p" -ne 0 ]&&[ "$a" -ne 0 ];then echo GATE_PASS >>status.txt;tail -1 base.log;else tail -8 base.log;exit 1;fi
