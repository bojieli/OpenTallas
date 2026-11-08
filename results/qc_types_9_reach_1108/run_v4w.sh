#!/bin/bash
# QC-TYPES-9/REACH 11-08: plan_qc53v4w dry path (latency, validate, G0C, count dry vs v4u2, elab + strict native bind)
set -u
Q=/srv/opentallas-scratch2/claude/qct9; W=$Q/reach; F=$Q/farm; cd $F
PD=physical/die_plan/qwen_compute/plan_of_record; P=$PD/plan_qc53v4w.json
A=physical/die_plan/qwen_compute/qc_start_1106/runtime/asbuilt_reach.json
mkdir -p $W/dry $W/lat
cp $W/plan_qc53v4w.json $P; cp $W/asbuilt_reach.json $A
date
python3 -B tools/die_plan/gen.py latency $P --inplace --out $W/lat > $W/dry/latency.txt 2>&1; echo "LATENCY rc $?" >> $W/dry/latency.txt
python3 -B - $PD/plan_qc53v4u.json $P >> $W/dry/latency.txt 2>&1 <<'PY'
import json,sys,collections
a=json.load(open(sys.argv[1]))['latency']['lanes']; b=json.load(open(sys.argv[2]))['latency']['lanes']
d={k:(a[k]['cycles'],b[k]['cycles']) for k in a if a[k]['cycles']!=b.get(k,{}).get('cycles')}
print('LAT changed lanes', len(d), 'only-in', set(a)^set(b)); print('LAT deltas', collections.Counter(y-x for x,y in d.values()))
print('LAT non-cwn changed', sorted(k for k in d if '__cwn' not in k))
PY
python3 -B tools/die_plan/schema.py validate $P > $W/dry/validate.txt 2>&1; echo "VALIDATE rc $?" >> $W/dry/validate.txt
python3 -B tools/die_plan/check.py $P --completeness --out $W/dry/g0c_plan_qc53v4w > $W/dry/check.txt 2>&1; echo "CHECK rc $?" >> $W/dry/check.txt
ln -sfn $Q/dry/g0c_plan_qc53v4u $W/dry/g0c_plan_qc53v4u
python3 -B $Q/cmp_dry.py $Q/rtp $PD $W/dry plan_qc53v4u plan_qc53v4w > $W/dry/compare.txt 2>&1; echo "CMP rc $?" >> $W/dry/compare.txt
date
python3 -B tools/die_plan/bind.py elab $P --out $W/bind_v4w --asbuilt $A > $W/elab.log 2>&1; echo "ELAB rc $?" >> $W/elab.log
date
python3 -B tools/die_plan/bind.py bind $P --out $W/bind_v4w --strict --asbuilt $A > $W/bind.log 2>&1; echo "BIND rc $?" >> $W/bind.log
date
