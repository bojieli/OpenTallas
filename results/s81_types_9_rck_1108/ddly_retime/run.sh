#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-s81-rck-1113/ddly_bundle
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
for mode in base mutant;do
 args=();if [ "$mode" = mutant ];then args+=(-DDDLY_RQ_MUT);fi
 verilator --binary --timing -j 4 -O1 -Wno-fatal -Wno-WIDTH --top-module tb -I. "${args[@]}" --Mdir "build_$mode" -o tb tb.sv ot_s81_kp4_ddly.sv ddly_new.sv ot_s81_kp4_common.sv sram_stubs.sv > "$mode.build.log" 2>&1
 set +e
 "./build_$mode/tb" > "$mode.log" 2>&1
 rc=$?
 set -e
 tail -5 "$mode.log"
 if [ "$mode" = base ];then test "$rc" = 0;else test "$rc" != 0;fi
done
