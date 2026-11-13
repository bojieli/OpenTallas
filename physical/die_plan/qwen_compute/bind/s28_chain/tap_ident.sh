#!/bin/bash
# tap_ident.sh REF_PLAN PLAN_IN PLAN_OUT TAG : tap identity check + guarded source_clock_port re-point (tap_ident.py)
set -u; B=/srv/opentallas-scratch2/claude/qc-s28-hf1c/bind; E=${EVENT_TREE:-/srv/opentallas-scratch2/claude/wt/qc-s28-event}
POR=physical/die_plan/qwen_compute/plan_of_record; TAG=$4; L=$B/work/tap_ident_$TAG.log
R=$E/$POR/zz_ti_ref_$TAG.json; I=$E/$POR/zz_ti_in_$TAG.json; O=$E/$POR/zz_ti_out_$TAG.json
rm -f $R $I $O; cp $1 $R; cp $2 $I
(cd $E && nice python3 -I $B/tap_ident.py $POR/zz_ti_ref_$TAG.json $POR/zz_ti_in_$TAG.json --out $POR/zz_ti_out_$TAG.json \
   --report $B/work/tap_ident_$TAG.json --eq $B/work/eq_tap_ident_$TAG.tsv) > $L 2>&1; rc=$?
[ $rc = 0 ] && cp $O $3; rm -f $R $I $O; echo "RC=$rc" >> $L; cat $L; exit $rc
