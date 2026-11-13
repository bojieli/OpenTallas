#!/bin/bash
# usage: reset_pad.sh PLAN_IN REF PLAN_OUT TAG   (runs reset_pad.py in the event tree plan folder)
set -u; E=${EVENT_TREE:-/srv/opentallas-scratch2/claude/wt/qc-s28-event}; B=/srv/opentallas-scratch2/claude/qc-s28-hf1c/bind; POR=physical/die_plan/qwen_compute/plan_of_record
TAG=$4; I=$E/$POR/zz_pad_in_$TAG.json; R=$E/$POR/zz_pad_ref_$TAG.json; O=$E/$POR/zz_pad_out_$TAG.json
rm -f $I $R $O; cp $1 $I; cp $2 $R
cd $E && nice -n 19 python3 -I $B/reset_pad.py $I $R $O $B/work/reset_pad_$TAG.json $B/work/eq_reset_pad_$TAG.tsv > $B/work/reset_pad_$TAG.log 2>&1; rc=$?
echo "RC=$rc" >> $B/work/reset_pad_$TAG.log; [ $rc = 0 ] && cp $O $3; rm -f $I $R $O; exit $rc
