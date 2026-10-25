#!/bin/bash
# S81 plan v4: generate, latency, G0 (+png), census coverage.  usage: run_v4.sh OUTDIR
# TOOL=<dir> selects the die_plan tool (default: this tree's tools/die_plan).
# Current tools include the approved M9 fold-face support.
set -e
R=$(cd "$(dirname "$0")/../../.." && pwd); D=${1:?OUTDIR}; IN=${IN:-$R/physical/die_plan/s81/inputs}
T=${TOOL:-$R/tools/die_plan}
python3 $R/physical/die_plan/s81/gen_plan_v4.py --asbuilt $IN/plan.json --census $IN/s81_lanes.tsv --out $D
mkdir -p $D/inputs && rm -rf $D/inputs/core_pins && cp -r $IN/core_pins $D/inputs/   # hard_cores pins_file is plan-dir relative
python3 $T/schema.py validate $D/die_plan.json
python3 $T/gen.py latency $D/die_plan.json --inplace --out $D/lat
# S81-XDIE 10-24: die IO windows (die_io.json sidecar); stage dies have no host link (RELEASE_RACK 2.1 S81.HOST): host
# traffic rides the stage-in pair WN2/WN3 (s_0N pair B) in-band -> s_0N_LP -> seqhost
python3 $T/die_io.py plan $D/die_plan.json --out $D/die_io.json --in-band-host lk_WN2=coll__lk_WN2__s_0N_LP+ctrl__s_0N_LP__seqhost,lk_WN3=coll__lk_WN3__s_0N_LP+ctrl__s_0N_LP__seqhost
(cd $D && python3 $T/check.py die_plan.json --out $D/g0 ${PNG---png})
python3 $R/physical/die_plan/s81/census_cov.py $D/die_plan.json $D/instance_map.json $IN/s81_lanes.tsv --out $D/census_cov.json
