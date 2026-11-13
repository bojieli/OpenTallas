#!/bin/bash
# QC-S28-BIND reset reach (class 5) on the event tree tools. usage: reach5.sh MODE(check|fix) PLAN REF_PLAN OUTTAG [TYPES_RE]
set -u; E=${EVENT_TREE:-/srv/opentallas-scratch2/claude/wt/qc-s28-event}; B=/srv/opentallas-scratch2/claude/qc-s28-hf1c/bind
POR=physical/die_plan/qwen_compute/plan_of_record
MODE=$1; PL=$2; REF=$3; TAG=$4; TY=${5:-}
O=$B/reach_$TAG; mkdir -p $O; SP=$E/$POR/zz_reach_$TAG.json; rm -f $SP; cp $PL $SP
RP=$E/$POR/zz_reach_ref.json; cmp -s $REF $RP || { rm -f $RP; cp $REF $RP; }
cd $E
if [ $MODE = check ]; then
  nice -n 19 python3 -I tools/die_plan/reach_fix.py check $SP --repo $E ${TY:+--types "$TY"} --json $O/check.json --tsv $O/check.tsv -j 16 > $O/check.log 2>&1; echo "RC=$?" >> $O/check.log
else
  nice -n 19 python3 -I tools/die_plan/reach_fix.py fix $SP --repo $E ${TY:+--types "$TY"} --classes 5 --ref-plan $RP --out-plan $O/plan_fix.json --event $O/event.json --json $O/fix.json --tsv $O/fix.tsv -j 16 > $O/fix.log 2>&1; echo "RC=$?" >> $O/fix.log
fi
