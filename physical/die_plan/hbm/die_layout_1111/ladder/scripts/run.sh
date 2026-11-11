#!/bin/bash
# usage: run.sh SPEC TAG  -> ld/out_TAG + ld/g0_TAG
W=/srv/opentallas-scratch3/claude/die-layout-hbm; cd $W/ld
nice -n 19 python3 -I ladder.py $W/repo/tools/die_plan $W/ev/plan $1 $W/ld/out_$2 > ladder_$2.log 2>&1 || exit 1
cd $W && bash g0.sh $W/ld/out_$2 $W/ld/g0_$2
python3 -I ld/g0diff.py b0/t10.g0/g0_report.json/g0_report.json ld/g0_$2/g0_report.json/g0_report.json 60 > ld/g0_$2/diff.txt 2>&1
echo DONE >> ld/g0_$2/diff.txt
