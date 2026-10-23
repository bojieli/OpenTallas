#!/bin/bash
# QDIE-R56: wait PRE_DONE of TAG, then NP probe controller + guarded diagnostic follow (phase2/phase3, HOLD_GRT armed).
set -u
T=${1:?tag}; R=/srv/opentallas-scratch/claude/codex-qdie-2000; M=/home/ubuntu/scratch/qdie-r56
while :; do
 status=$(timeout 30 ssh -o ControlPath=none ot-gold1 "if [ -e $R/$T/FINAL_GEN_FAIL ]; then echo FAIL; elif [ -e $R/$T/PRE_DONE ]; then echo PRE; fi")
 [ "$status" = FAIL ] && { echo "$T GEN failed, no follow"; exit 4; }
 [ "$status" = PRE ] && break
 sleep 60
done
bash "$M/probe_np_chain.sh" "$T" > "$M/$T.npwatch.log" 2>&1 &
echo "NP controller $!" >> "$M/$T.controllers"
/home/ubuntu/bin/ot-run --mem 200 --threads 8 --disk 100 --priority die --dir "$R/$T" -- bash "$R/$T/guarded_follow.sh"
echo "follow rc=$?"
