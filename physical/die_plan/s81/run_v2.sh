#!/bin/bash
# usage: run_v2.sh OUTDIR TOOLROOT   (TOOLROOT = checkout of claude/plan-tool-1023 >= dd4c59718)
set -e
D=$1; T=$2
S=$(cd "$(dirname "$0")" && pwd)
python3 $S/gen_plan_v2.py --asbuilt /home/ubuntu/scratch/plan-s81/in/plan.json --census /home/ubuntu/scratch/plan-s81/in/s81_lanes.tsv --out $D
cd $T
python3 tools/die_plan/schema.py validate $D/die_plan.json
python3 tools/die_plan/gen.py latency $D/die_plan.json --inplace --out $D/lat
python3 tools/die_plan/check.py $D/die_plan.json --out $D/g0 --png
