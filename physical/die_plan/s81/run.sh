#!/bin/bash
# usage: run.sh OUTDIR [gen args]
set -e
D=$1; shift
S=$(cd "$(dirname "$0")" && pwd)
python3 $S/gen_plan.py --asbuilt /home/ubuntu/scratch/plan-s81/in/plan.json --census /home/ubuntu/scratch/plan-s81/in/s81_lanes.tsv --out $D "$@" > $D.gen.log
python3 $S/to_schema.py $D > $D.schema.log
cd /home/ubuntu/wt/plan-tool-1023 && python3 tools/die_plan/schema.py validate $D/die_plan.json 2>&1 | sort | uniq -c | sort -rn | head -20
python3 tools/die_plan/gen.py latency $D/die_plan.json --inplace --out $D/lat > $D.lat.log 2>&1 || tail -3 $D.lat.log
python3 tools/die_plan/check.py $D/die_plan.json --out $D/g0 --png > $D.g0.log 2>&1 || true; tail -1 $D.g0.log
python3 -c "
import json,collections as C;r=json.load(open('$D/g0/g0_report.json'))
f=r['findings'];print(C.Counter((e.get('level'),e.get('check')) for e in f))
seen=set()
for e in f:
  k=(e.get('level'),e.get('check'))
  if k not in seen and e['level']=='ERROR': seen.add(k); print(json.dumps(e)[:300])
"
