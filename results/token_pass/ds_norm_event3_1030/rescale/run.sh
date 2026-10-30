#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
R=/srv/opentallas-scratch2/claude/codex-ds-current-rescale-1030
cd "$R"
python3 stage.py "$R" >stage.log 2>&1
verilator --binary --timing -O1 -fno-dfg --unroll-count 4 -Wno-fatal -Wno-WIDTH -Wno-PINMISSING --top-module tb_norm_rescale --Mdir obj -j 2 --output-groups 16 --output-split 5000 --output-split-cfuncs 500 -f defines.f -f source.f tb_norm_rescale.sv -MAKEFLAGS 'OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0' >build.log 2>&1
set +e
obj/Vtb_norm_rescale >base.log 2>&1;b=$?
obj/Vtb_norm_rescale +bad_rstd >bad_rstd.log 2>&1;m=$?
printf 'BASE_RC=%s\nBAD_RSTD_RC=%s\n' "$b" "$m" >status.txt
cat status.txt
if [ "$b" -eq 0 ]&&[ "$m" -ne 0 ];then echo GATE_PASS >>status.txt;tail -7 base.log;else tail -10 base.log;exit 1;fi
