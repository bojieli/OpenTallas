#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-s81-rck-0222/work
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
E=$PWD/results/s81_rck_11_reform_1108/rxb_face
D=$PWD/../rxb_face_proof
mkdir -p "$D"
for mode in base mutant;do
 args=();if [ "$mode" = mutant ];then args+=(-DRXB_RET_MUT_BIAS);fi
 verilator --binary --timing -j 8 -O1 -Wno-fatal -Wno-WIDTH -DOT_S81_RCK_REFORM -DOT_S81_RCK_RELAY4 -DOT_S81_KP4_AM_FACE3 -DOT_S81_KP4_SYN_LOCAL -DOT_S81_LPL_CHUNK -DOT_S81_RCK_RXB_FACE_RET "${args[@]}" --top-module tb --Mdir "$D/$mode" -o tb "$E/tb.sv" rtl/common/landed_parent/ot_pl_land.sv rtl/dsrom_sys/s81_link/col/ot_s81_rck_reform.sv > "$E/$mode.build.log" 2>&1
 set +e
 "$D/$mode/tb" > "$E/$mode.log" 2>&1
 rc=$?
 set -e
 tail -5 "$E/$mode.log"
 if [ "$mode" = base ];then test "$rc" = 0;else test "$rc" != 0;fi
done
