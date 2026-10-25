#!/bin/bash
# KV-CORES/ASTK 10-25: route (resume from 3_place, in-flow HOLD_SLACK_MARGIN 5) -> warm m8 post-route ECO -> signoff.
#   astk_chain.sh KIT   (run detached on epyc1; heavy steps through ot-run)
set -uo pipefail
K=$1; WT=/srv/opentallas-scratch2/claude/wt/kv-cores-astk; H=$WT/physical/die_plan/qwen_kvsys/cores/harden
OTR=~/.local/bin/ot-run
echo "$(date) route $K"
$OTR --mem 32 --threads 16 --stage $K --dir $K -- bash $K/run_kit_kv.sh $K route 32 16
echo "$(date) route rc=$?"
test -f $(ls -d $K/run/results/asap7/*/base)/5_2_route.odb || { echo "no routed odb"; exit 1; }
E=${K}.m8
bash $H/eco/mk_eco.sh $K $E m8 $WT || exit 1; cp $H/eco/run_eco.sh $E/
echo "$(date) eco m8 $E"
$OTR --mem 32 --threads 8 --stage $E --dir $E -- bash $E/run_eco.sh $E 8 32
echo "$(date) eco rc=$?"
