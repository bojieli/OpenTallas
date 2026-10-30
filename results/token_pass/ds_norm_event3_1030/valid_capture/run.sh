#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
R=/srv/opentallas-scratch2/claude/codex-ds-valid-partial-1030
cd "$R"
verilator --binary --timing -O1 -fno-dfg --unroll-count 4 -Wno-fatal -Wno-WIDTH -Wno-PINMISSING --top-module tb_valid_partial --Mdir obj -j 2 --output-groups 16 --output-split 5000 --output-split-cfuncs 500 -f defines.f -f source.f tb_valid_partial.sv -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0' >build.log 2>&1
set +e
obj/Vtb_valid_partial >base.log 2>&1;b=$?
obj/Vtb_valid_partial +bad_payload >payload.log 2>&1;p=$?
printf 'BASE_RC=%s\nPAYLOAD_RC=%s\n' "$b" "$p" >status.txt
cat status.txt
if [ "$b" -eq 0 ]&&[ "$p" -ne 0 ];then echo GATE_PASS >>status.txt;tail -4 base.log;else tail -10 base.log;exit 1;fi
