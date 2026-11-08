#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-s81-rck-0222/work
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
E=$PWD/results/s81_rck_11_reform_1108/rxs_control
D=$PWD/../rxs_control_proof
mkdir -p "$D"
for mode in base mutant; do
 args=();if [ "$mode" = mutant ];then args+=(-DRXS_CTL_MUT);fi
 verilator --binary --timing -j 8 -O1 -Wno-fatal -Wno-WIDTH --top-module tb --Mdir "$D/$mode" -o tb -Irtl/dsrom_sys/s81_link "${args[@]}" "$E/tb.sv" rtl/dsrom_sys/s81_link/ot_s81_kp4_bm.sv rtl/dsrom_sys/s81_link/ot_s81_kp4_common.sv > "$E/$mode.build.log" 2>&1
 set +e
 "$D/$mode/tb" > "$E/$mode.log" 2>&1
 rc=$?
 set -e
 tail -4 "$E/$mode.log"
 if [ "$mode" = base ];then test "$rc" = 0;else test "$rc" != 0;fi
done
