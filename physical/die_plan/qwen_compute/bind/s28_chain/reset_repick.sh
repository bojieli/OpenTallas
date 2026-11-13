#!/bin/bash
# usage: reset_repick.sh PLAN_IN PLAN_OUT TAG [BASE=in/zz_c1_taps.json]
set -u; E=${EVENT_TREE:-/srv/opentallas-scratch2/claude/wt/qc-s28-event}; B=/srv/opentallas-scratch2/claude/qc-s28-hf1c/bind; POR=physical/die_plan/qwen_compute/plan_of_record
TAG=$3; BASE=${4:-$B/in/zz_c1_taps.json}; I=$E/$POR/zz_rp_in_$TAG.json; Bs=$E/$POR/zz_rp_base_$TAG.json; O=$E/$POR/zz_rp_out_$TAG.json
rm -f $I $Bs $O; cp $1 $I; cp $BASE $Bs
cd $E && nice -n 19 python3 -I $B/reset_repick.py $POR/zz_rp_base_$TAG.json $POR/zz_rp_in_$TAG.json $POR/zz_rp_out_$TAG.json $B/work/reset_repick_$TAG.json $B/work/eq_reset_repick_$TAG.tsv > $B/work/reset_repick_$TAG.log 2>&1; rc=$?
echo "RC=$rc" >> $B/work/reset_repick_$TAG.log; [ $rc = 0 ] && cp $O $2; rm -f $I $Bs $O; exit $rc
