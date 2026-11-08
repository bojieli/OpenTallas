#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-s81-rck-1113/work
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
E=$PWD/results/s81_types_9_rck_1108/bm_tail
D=$PWD/../bm_tail_proof
mkdir -p "$D"
for mode in base mutant; do
 args=();if [ "$mode" = mutant ];then args+=(-DRXS_CTL_MUT);fi
 verilator --binary --timing --x-initial unique --x-assign unique -j 8 -O1 -Wno-fatal -Wno-WIDTH --top-module tb --Mdir "$D/$mode" -o tb -Irtl/dsrom_sys/s81_link "${args[@]}" "$E/tb.sv" "$E/reference.sv" rtl/dsrom_sys/s81_link/ot_s81_kp4_bm.sv rtl/dsrom_sys/s81_link/ot_s81_kp4_common.sv > "$E/$mode.build.log" 2>&1
 for seed in 1 2 3; do
 set +e
 "$D/$mode/tb" +verilator+rand+reset+2 +verilator+seed+$seed > "$E/${mode}_s${seed}.log" 2>&1
 rc=$?
 set -e
 tail -5 "$E/${mode}_s${seed}.log"
 if [ "$mode" = base ];then test "$rc" = 0;else test "$rc" != 0;break;fi
 done
done
