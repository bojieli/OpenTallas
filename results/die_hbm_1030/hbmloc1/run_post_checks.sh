#!/bin/bash
# HBM-LOC-1: post-fix pipeline (DIE-HBM-23 order_fix/post_fix/post_fix2/post_fix3 + gen.py latency) on out_$1/die_plan.json
# into plan/$1, then G0 + G0C + strict all-gap bind (same command/asbuilt as DIE-HBM-40 run_checks.sh; tools = wt/hbm-loc-1,
# no diff vs claude/die-hbm-40-1030 tools/die_plan).  usage: run_post_checks.sh VARIANT
set -u
R=/srv/opentallas-scratch2/claude/hbm-loc-1; WT=/srv/opentallas-scratch2/claude/wt/hbm-loc-1; V=$1
RP=$WT/results/die_hbm_1029/hbm23/replan; TD=$WT/tools/die_plan
ulimit -v 30000000
mkdir -p $R/plan/$V $R/g0/$V $R/bind/$V/out; ln -sfn /srv/opentallas-scratch2/claude/hbm-bind-13-1029/g3/out/asbuilt.json $R/bind/$V/out/asbuilt.json  # yosys elab of the as-built top, lane-independent, as DIE-HBM-41
cp -a $R/out_$V/. $R/plan/$V/
rm -f $R/plan/$V/lat; rm -f $R/plan/$V/replan_report.json; cp $R/out_$V/replan_report.json $R/plan/$V/; mkdir -p $R/plan/$V/lat
PL=$R/plan/$V/die_plan.json
{ python3 $RP/order_fix.py $TD $PL && python3 $RP/post_fix.py $PL $R/plan/$V/replan_report.json && python3 $RP/post_fix2.py $PL \
  && python3 $RP/post_fix3.py $TD $PL && (cd $WT && python3 tools/die_plan/gen.py latency $PL --inplace --out $R/plan/$V/lat); } > $R/plan/$V/postfix.log 2>&1
echo $? > $R/plan/$V/postfix.rc
cd $WT
( python3 tools/die_plan/check.py $PL --out $R/g0/$V/g0_report.json > $R/g0/$V/g0.log 2>&1; echo $? > $R/g0/$V/g0.rc
  python3 tools/die_plan/check.py $PL --completeness --out $R/g0/$V/g0c_report.json > $R/g0/$V/g0c.log 2>&1; echo $? > $R/g0/$V/g0c.rc ) &
python3 -u tools/die_plan/bind.py bind $PL --asbuilt /srv/opentallas-scratch2/claude/die-hbm-39/bind/asbuilt.json --out $R/bind/$V/out --strict --all-gaps --mem 24 > $R/bind/$V/bind.log 2>&1; echo $? > $R/bind/$V/bind.rc
wait; touch $R/bind/$V/done
