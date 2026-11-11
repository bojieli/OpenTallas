#!/bin/bash
# DS85-LATETAP-1111 (DO_NOT_COUNT): DIE-RECHECK-1 s81_clock_auto.sh recipe (kit + post_kit) on a prepared variant dir
#   run_pad.sh VARIANT   (s81/auto/VARIANT holds repo/ map.json feed_bal.json kit.yaml [tap_pad.json])
set -uo pipefail
cd /
W=/srv/opentallas-scratch2/claude/ds85-latetap
V=$1; A=$W/s81/auto/$V
REPO=$A/repo; PLAN=$REPO/physical/die_plan/s81/plan_feedbal_1111.json; TOOLS=$REPO/tools/die_plan
echo "run $V plan $PLAN $(date)" > $A/auto.log
rm -rf $W/s81/ck_$V
python3 -s $REPO/tools/clk/ot_clk.py kit $A/kit.yaml --out $W/s81/ck_$V --workers 24 > $A/kit.log 2>&1 || { echo FAIL kit >> $A/auto.log; exit 23; }
echo "kit ok" >> $A/auto.log
PLAN=$PLAN TOOLS=$TOOLS AUTO=1 $W/scripts/post_kit.sh $V >> $A/auto.log 2>&1 || { echo FAIL post_kit rc=$? >> $A/auto.log; exit 24; }
echo RUN_DONE >> $A/auto.log
