#!/bin/bash
W=/srv/opentallas-scratch/claude/wt/s81-kits-1024r-nodes; P=/srv/opentallas-scratch/claude/rtlc_bench/plan
cd $W
rm -rf $P/new $P/base; mkdir -p $P
( PNG= nice bash physical/die_plan/s81/run_v4.sh $P/new > $P/new.log 2>&1; echo rc=$? >> $P/new.log; nice python3 tools/die_plan/check.py --completeness $P/new/die_plan.json > $P/new_compl.log 2>&1; echo rc=$? >> $P/new_compl.log ) &
( git show HEAD:physical/die_plan/s81/gen_plan_v4.py > physical/die_plan/s81/gen_plan_v4_rtlcbase_tmp.py && mkdir -p $P/base && nice python3 physical/die_plan/s81/gen_plan_v4_rtlcbase_tmp.py --asbuilt physical/die_plan/s81/inputs/plan.json --census physical/die_plan/s81/inputs/s81_lanes.tsv --out $P/base > $P/base.log 2>&1 && mkdir -p $P/base/inputs && cp -r physical/die_plan/s81/inputs/core_pins $P/base/inputs/ && nice python3 tools/die_plan/gen.py latency $P/base/die_plan.json --inplace --out $P/base/lat >> $P/base.log 2>&1; echo rc=$? >> $P/base.log; rm -f physical/die_plan/s81/gen_plan_v4_rtlcbase_tmp.py ) &
wait
