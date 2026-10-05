#!/bin/bash
# Exactness re-proof of the closure RTL (SEQ_LA=1, DEC_LA=1) on the adopted 8K benches: verify layer 0 with commit/rollback
# (k_L0), AR layer 0 (k_AR0), verify heads p=4 with the accept unit (c_H1 a=0, c_H2 a=3), drafter layer 0 at
# start 8188 with the real-magnitude window (k_D0r).  Same plans/goldens as results/rtl/qwen_dspark_system_20261004.
R=/srv/opentallas-scratch/claude/qwen-core-decode; R0=/srv/opentallas-scratch/claude/qwen-dspark-closure; E=/srv/opentallas-scratch/claude/qwen-dspark-system
SRC=$1; BLD=$2; TAG=$3; shift 3
mkdir -p $R/proof/$TAG/res $R/proof/$TAG/runs
cd $SRC
step() { echo "$(date -u +%FT%TZ) $*" >> $R/proof/$TAG/chain.log; }
run() { local n=$1 j=$2 th=$3; shift 3
  step "$n start"
  /srv/opentallas-scratch/admit.sh 16 -- python3 tools/qwen_rom_rt_vprm_w12.py --workdir $R/proof/$TAG/runs/$n --build-dir $BLD \
     --hbm-layers 3 --code-banks 1 --plan $j/plan --expect $j/expect.json --result $R/proof/$TAG/res/$n.json --threads $th "$@" \
     > $R/proof/$TAG/runs/$n.out 2>&1
  echo $? > $R/proof/$TAG/runs/$n.rc; step "$n rc=$(cat $R/proof/$TAG/runs/$n.rc)"; }
run k_L0 $E/ctx8k/plans/L0 6 --kv-dir $E/ctx8k/plans/kv "$@" &
run k_AR0 $E/ctx8k/plans/AR0 4 --kv-dir $E/ctx8k/plans/kv "$@" &
run c_H1 $E/comp/H1 4 "$@" &
run c_H2 $E/comp/H2 4 "$@" &
run k_D0r $R0/d8k/dgold8k_real 6 --kv-dir $R0/d8k/dgold8k_real/kv "$@" &
wait
step done
