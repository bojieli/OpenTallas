#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-s81-rck-1113/bm_tail_bundle
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
E=$PWD
D=$PWD/build_zero
mkdir -p "$D"
for mode in base mutant; do
 args=();if [ "$mode" = mutant ];then args+=(-DRXS_CTL_MUT);fi
 verilator --binary --timing --x-initial unique --x-assign unique -j 8 -O1 -Wno-fatal -Wno-WIDTH --top-module tb --Mdir "$D/$mode" -o tb -I. "${args[@]}" "$E/tb_zero.sv" "$E/reference.sv" ot_s81_kp4_bm.sv ot_s81_kp4_common.sv > "$E/$mode.build_zero.log" 2>&1
 for seed in 11; do
 set +e
 "$D/$mode/tb" +verilator+rand+reset+2 +verilator+seed+$seed > "$E/${mode}_zero_s${seed}.log" 2>&1
 rc=$?
 set -e
 tail -5 "$E/${mode}_zero_s${seed}.log"
 if [ "$mode" = base ];then test "$rc" = 0;else test "$rc" != 0;break;fi
 done
done
