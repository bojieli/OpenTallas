#!/bin/bash
# usage: g0c_try.sh PLANJSON TAG  -> G0C findings delta vs main base
W=/srv/opentallas-scratch2/claude/die-kv-50/wt-phy; G=/srv/opentallas-scratch2/claude/die-kv-50/g0c
cd $W/physical/die_plan/qwen_kvsys && cp $1 plan_of_record/plan_try_$2.json && (ulimit -v 33554432; nice python3 ../../../tools/die_plan/check.py plan_of_record/plan_try_$2.json --completeness > $G/$2.out 2>&1); mv plan_of_record/g0_report.json $G/$2_report.json; rm plan_of_record/plan_try_$2.json
python3 - $G/base_report.json $G/$2_report.json <<"PY"
import json,collections,sys
f=lambda p: collections.Counter(json.dumps(x,sort_keys=True) for x in json.load(open(p))["findings"])
b=f(sys.argv[1]); n=f(sys.argv[2]); print("vs main: new", sum((n-b).values()), "gone", sum((b-n).values()))
for x in (n-b): print(" +", x[:260])
for x in (b-n): print(" -", x[:260])
PY
