#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
cd /srv/opentallas-scratch2/claude/codex-ds-pdsk-consumer-1030
verilator --binary --timing -O1 -j 2 -Wno-fatal -Wno-WIDTH -Wno-PINMISSING --top-module tb_pdsk_repair --Mdir obj src/ot_rst_relay.sv src/ot_s81sl_xrt.sv tb_pdsk_repair.sv >build.log 2>&1
set +e
obj/Vtb_pdsk_repair >base.log 2>&1;b=$?
obj/Vtb_pdsk_repair +old_actual_calendar >old_actual.log 2>&1;o=$?
obj/Vtb_pdsk_repair +wrong_selector >wrong_selector.log 2>&1;s=$?
obj/Vtb_pdsk_repair +wrong_date >wrong_date.log 2>&1;d=$?
printf 'BASE_RC=%s\nOLD_ACTUAL_RC=%s\nWRONG_SELECTOR_RC=%s\nWRONG_DATE_RC=%s\n' "$b" "$o" "$s" "$d" >status.txt
cat status.txt
if [ "$b" -eq 0 ]&&[ "$o" -ne 0 ]&&[ "$s" -ne 0 ]&&[ "$d" -ne 0 ];then echo GATE_PASS >>status.txt;else tail -12 base.log;exit 1;fi
