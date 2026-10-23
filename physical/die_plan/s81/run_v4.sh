#!/bin/bash
# S81 plan v4: generate, latency, G0 (+png), census coverage.  usage: run_v4.sh OUTDIR
# TOOL=<dir> selects the die_plan tool (default: this tree's tools/die_plan).
# Current tools include the approved M9 fold-face support.
set -e
R=$(cd "$(dirname "$0")/../../.." && pwd); D=${1:?OUTDIR}; IN=${IN:-$R/physical/die_plan/s81/inputs}
T=${TOOL:-$R/tools/die_plan}
python3 $R/physical/die_plan/s81/gen_plan_v4.py --asbuilt $IN/plan.json --census $IN/s81_lanes.tsv --out $D
python3 $T/schema.py validate $D/die_plan.json
python3 $T/gen.py latency $D/die_plan.json --inplace --out $D/lat
(cd $D && python3 $T/check.py die_plan.json --out $D/g0 --png)
python3 $R/physical/die_plan/s81/census_cov.py $D/die_plan.json $D/instance_map.json $IN/s81_lanes.tsv --out $D/census_cov.json
