#!/bin/bash
set -eu
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
cd /work
cp /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef tech.lef
openroad -no_init -exit fixture.tcl > fixture.log 2>&1
openroad -no_init -exit -python export_geometry.py > export.log 2>&1
python3 verify_geometry.py geometry.json --output verification.json
python3 - <<'PY'
import json
p=json.load(open('geometry.json'))
for i in p['instances']:
 for n in ['VDD','VSS']:
  pins=[x for x in i['pins'] if x[0]==n and x[2]=='M4']
  assert pins,(i['name'],n,'no actual declared power pins')
print('HBM_PHY_ALL_4_ACTUAL_INSTANCES_DECLARE_BOTH_M4_SUPPLIES')
PY
cp hbm.lef hbm.candidate.lef.txt
trap 'cp hbm.candidate.lef.txt hbm.lef' EXIT
cp hbm.original.lef.txt hbm.lef
if openroad -no_init -exit fixture.tcl > historical_mutant.log 2>&1; then exit 1; fi
grep -q 'missing declared VDD' historical_mutant.log
cp hbm.candidate.lef.txt hbm.lef
echo 'HBM_PHY_DECLARED_GEOMETRY_PASS; ASSUMED EXTERNAL POWER ONLY; NO ANALOG/IR QUALIFICATION'
