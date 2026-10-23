#!/bin/bash
# S81 plan v3: generate, latency, G0 (+png), census coverage.  usage: run_v3.sh OUTDIR
set -e
R=$(cd "$(dirname "$0")/../../.." && pwd); D=${1:?OUTDIR}; IN=${IN:-/home/ubuntu/scratch/plan-s81/in}
python3 $R/physical/die_plan/s81/gen_plan_v3.py --asbuilt $IN/plan.json --census $IN/s81_lanes.tsv --out $D
python3 $R/tools/die_plan/schema.py validate $D/die_plan.json
python3 $R/tools/die_plan/gen.py latency $D/die_plan.json --inplace --out $D/lat
python3 $R/tools/die_plan/check.py $D/die_plan.json --out $D/g0 --png
python3 $R/physical/die_plan/s81/census_cov.py $D/die_plan.json $D/instance_map.json $IN/s81_lanes.tsv --out $D/census_cov.json
