#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
R=/srv/opentallas-scratch2/claude/codex-ds-rstd-return-1030
cd "$R"
python3 stage.py "$R" >stage.log 2>&1
verilator --binary --timing -O1 -fno-dfg --unroll-count 4 -Wno-fatal -Wno-WIDTH -Wno-PINMISSING --top-module tb_rstd_return --Mdir obj -j 2 --output-groups 16 --output-split 5000 --output-split-cfuncs 500 -f defines.f -f source.f tb_rstd_return.sv -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0' >build.log 2>&1
set +e
obj/Vtb_rstd_return +FCLK_SHIFT_PS=0 >phase0.log 2>&1;a=$?
obj/Vtb_rstd_return +FCLK_SHIFT_PS=166 >phase166.log 2>&1;b=$?
obj/Vtb_rstd_return +FCLK_SHIFT_PS=-166 >phase_m166.log 2>&1;c=$?
obj/Vtb_rstd_return +FCLK_SHIFT_PS=0 +bad_link >bad_link.log 2>&1;m=$?
printf 'PHASE0_RC=%s\nPHASE166_RC=%s\nPHASE_M166_RC=%s\nBAD_LINK_RC=%s\n' "$a" "$b" "$c" "$m" >status.txt
cat status.txt
if [ "$a" -eq 0 ]&&[ "$b" -eq 0 ]&&[ "$c" -eq 0 ]&&[ "$m" -ne 0 ];then echo GATE_PASS >>status.txt;else tail -8 phase0.log;exit 1;fi
