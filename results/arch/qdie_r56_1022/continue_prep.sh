#!/bin/bash
# QDIE-R56: wait PRE_DONE of TAG, then (if not already running) the NP probe controller + the PREP-ONLY guarded follow
# (diag gate -> phase2 -> phase3 OT_STOP=prep: case/PDN/die clock, PREPARED_WAIT_GRT; GRT is a separate resume200 job).
set -u
T=${1:?tag}; R=/srv/opentallas-scratch/claude/codex-qdie-2000; M=/home/ubuntu/scratch/qdie-r56
while :; do
 status=$(timeout 30 ssh -o ControlPath=none ot-gold1 "if [ -e $R/$T/FINAL_GEN_FAIL ]; then echo FAIL; elif [ -e $R/$T/PRE_DONE ]; then echo PRE; fi")
 [ "$status" = FAIL ] && { echo "$T GEN failed, no follow"; exit 4; }
 [ "$status" = PRE ] && break
 sleep 60
done
if ! pgrep -f "probe_np_chain.sh $T\$" >/dev/null; then
  bash "$M/probe_np_chain.sh" "$T" > "$M/$T.npwatch.log" 2>&1 &
  echo "NP controller $!" >> "$M/$T.controllers"
fi
/home/ubuntu/bin/ot-run --mem 32 --threads 8 --disk 5 --priority die --dir "$R/$T" -- bash "$R/$T/guarded_prep.sh"
echo "prep follow rc=$?"
