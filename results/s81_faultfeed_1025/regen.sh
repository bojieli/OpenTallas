#!/bin/bash
# S81-PORTS: regen S81 plan from SRC (generator) with exact FT sites reused from SEED plan; then latency + G0 + G0C
set -euo pipefail
SRC=$1; OUT=$2; SEED=$3
rm -rf $OUT; mkdir -p $OUT
cd $SRC
PNG= bash physical/die_plan/s81/run_v4.sh $OUT/gen > $OUT/gen.log 2>&1
python3 tools/die_plan/ft_sites.py $OUT/gen/die_plan.json --all-core-types --reuse $SEED --out $OUT/gen/die_plan_ft.json --ledger $OUT/ft_ledger.json > $OUT/ft.log 2>&1
mv $OUT/gen/die_plan_ft.json $OUT/gen/die_plan.json
python3 tools/die_plan/schema.py validate $OUT/gen/die_plan.json > $OUT/schema.log 2>&1
python3 tools/die_plan/gen.py latency $OUT/gen/die_plan.json --inplace --out $OUT/gen/lat > $OUT/lat.log 2>&1
set +e; cd $OUT/gen
python3 $SRC/tools/die_plan/check.py die_plan.json --out $OUT/g0 > $OUT/g0.log 2>&1; echo "G0 rc=$?" >> $OUT/rc.txt
python3 $SRC/tools/die_plan/check.py die_plan.json --completeness --out $OUT/g0c > $OUT/g0c.log 2>&1; echo "G0C rc=$?" >> $OUT/rc.txt
tail -2 $OUT/g0c.log
