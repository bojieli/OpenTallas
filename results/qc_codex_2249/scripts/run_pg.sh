#!/bin/bash
set -euo pipefail
V=$1
Q=/srv/opentallas-scratch2/claude
R=$Q/codex-qc-2249
I=$Q/codex-qc-import-0824
O=$R/pg_$V
mkdir -p "$O"
if [ "$V" = A ]; then
 CMD="python $I/src/plan_access.py --input $R/readback --clock-seed $R/reservation/clock_seed.json --joint-clock-reserved $R/reservation/joint_reserved.json --reserved-power $I/nativepg/bridges/reserved_bridges.json --out $O"
else
 CMD="python $Q/die-qc36/pg_access_plan_b7a872287.py --input $R/readback --clock-seed $R/reservation/clock_seed.json --joint-clock-reserved $R/reservation/joint_reserved.json --m9-select cover --m8-landing fallback --out $O"
fi
python3 -c "import json; p=json.load(open('$R/readback/summary.json')); assert p['verdict']=='ACTUAL_REACH_PASS' and p['power_contacts']==198762"
docker run --rm --name codexqc2249-pg$V-$$ --memory=96g --memory-swap=96g --cpus=4 -v "$Q:$Q" -e PYTHONPATH="$I/pydeps" python:3.12 bash -c "set -e; trap 'chown -R 1000:1000 $O' EXIT; $CMD > $O/run.log 2>&1"
