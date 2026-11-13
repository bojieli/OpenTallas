#!/bin/bash
# usage: reset_reach.sh TAG PLAN [PLAN...]  -> work/reset_reach_TAG.json (plans copied into the tree plan folder)
set -u; E=${EVENT_TREE:-/srv/opentallas-scratch2/claude/wt/qc-s28-event}; B=/srv/opentallas-scratch2/claude/qc-s28-hf1c/bind; POR=physical/die_plan/qwen_compute/plan_of_record
TAG=$1; shift; L=(); i=0
for p in "$@"; do d=$E/$POR/zz_rr_${TAG}_$i.json; rm -f $d; cp $p $d; L+=($POR/zz_rr_${TAG}_$i.json); i=$((i+1)); done
cd $E && nice -n 19 python3 -I $B/reset_reach.py "${L[@]}" --json $B/work/reset_reach_$TAG.json > $B/work/reset_reach_$TAG.log 2>&1; echo "RC=$?" >> $B/work/reset_reach_$TAG.log
