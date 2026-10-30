#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
TASK=/srv/opentallas-scratch2/claude/codex-ds-current-xfin-1030
cd "$TASK"
python3 stage.py "$TASK" >stage.log 2>&1
verilator --binary --timing -O1 -fno-dfg --unroll-count 4 -Wno-fatal -Wno-WIDTH -Wno-PINMISSING --top-module tb_norm_xfin_source --Mdir obj -j 2 --output-groups 16 --output-split 5000 --output-split-cfuncs 500 -f defines.f -f source.f tb_current_xfin.sv -MAKEFLAGS 'OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0' >build.log 2>&1
set +e
obj/Vtb_norm_xfin_source +DIR="$TASK" >base.log 2>&1;b=$?
obj/Vtb_norm_xfin_source +DIR="$TASK" +MUT=1 >duplicate_sid.log 2>&1;d=$?
printf 'BASE_RC=%s\nDUPLICATE_SID_RC=%s\n' "$b" "$d" >status.txt
cat status.txt
if [ "$b" -eq 0 ]&&[ "$d" -ne 0 ];then echo GATE_PASS >>status.txt;tail -7 base.log;else tail -10 base.log;exit 1;fi
