#!/bin/bash
# HARD-S81-DSDV-1: XS4-CORE event bind (pattern events/s81_ready12bA_1112/run_r12bA_dst.sh).
#   tree D = bsrc_xs4 (FIN bsrc_r12bA_dst bulk + origin/main 87b85b86bd rtl/ tools/ + this lane files); asbuilt base = bbase_xs4.
#   usage: run_bind_xs4.sh PLAN.json TAG     -> OUT=$F/out_$TAG, logs $F/$TAG.*
set -u
F=/srv/opentallas-scratch2/claude/hard-s81-dsdv-1; D=$F/bsrc_xs4; PL=$1; TAG=$2; OUT=$F/out_$TAG
P=physical/die_plan/s81/plan_xs4.json; AB=${AB:-$F/asbuilt_xs4b.json}
SEED=${SEED:-/srv/opentallas-scratch2/claude/s81-r12ba-fin/out_r12bA_dst}
export PYTHONDONTWRITEBYTECODE=1; set -o pipefail
test ! -e $OUT || { echo "REFUSE $OUT exists"; exit 3; }
cp --remove-destination $PL $D/$P
cp --remove-destination $PL $D/physical/die_plan/s81/plan_h2_2249.json
echo "plan $(sha256sum < $D/$P | cut -c1-12) asbuilt $(sha256sum < $AB | cut -c1-12)"
cd $D || exit 9
mkdir -p $OUT; [ "${NOSEED:-0}" = 1 ] || { cp -a $SEED/. $OUT/; rm -rf $OUT/rtl $OUT/bind_report.json $OUT/verify; }
[ "${NOSEED:-0}" = 1 ] && { nice -n 5 python3 -I -B tools/die_plan/bind.py elab $P --asbuilt $AB --out $OUT --mem 48 > $F/$TAG.elab.log 2>&1; echo ELAB_RC=$?; }
nice -n 5 python3 -I -B tools/die_plan/bind.py bind $P --asbuilt $AB --out $OUT --strict > $F/$TAG.bind.log 2>&1; rc=$?; echo BIND_RC=$rc
[ $rc = 0 ] || exit 4
python3 -I -B tools/die_plan/lane_asbuilt_latency.py $OUT $D/$P --asbuilt $AB --pricing as-bound --tsv $F/$TAG.lat.tsv --json $F/$TAG.lat.json > $F/$TAG.lat.log 2>&1; rc=$?
echo LATCHECK_RC=$rc; tail -n 1 $F/$TAG.lat.log | cut -c1-300
echo RUN_DONE
