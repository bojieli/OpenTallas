#!/bin/bash
set -eu
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
cd /work
cp /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef tech.lef
openroad -no_init -exit fixture.tcl > fixture.log 2>&1
openroad -no_init -exit -python export_geometry.py > export.log 2>&1
python3 verify_geometry.py geometry.json --output verification.json
# Negative fixture: historical LEF has no legal declared M5 power access.
cp serdes.lef serdes.candidate.lef.txt
trap 'cp serdes.candidate.lef.txt serdes.lef' EXIT
cp serdes.original.lef.txt serdes.lef
if openroad -no_init -exit fixture.tcl > historical_mutant.log 2>&1; then
 echo 'Historical inaccessible abstract unexpectedly passed' >&2; exit 1
fi
grep -q 'historical LEF forbidden' historical_mutant.log
cp serdes.candidate.lef.txt serdes.lef
python3 - <<'PY'
import json
from verify_geometry import verify
p=json.load(open('geometry.json'))
s=next(s for s in p['shapes'] if s[1]=='M5' and s[-1]=='wire')
p['shapes'].append(['VSS' if s[0]=='VDD' else 'VDD',*s[1:]])
r=verify(p)
assert r['status']=='FAIL' and r['shorts']>0,r
json.dump(r,open('short_mutant.json','w'),indent=2)
print('SHORT_MUTANT_DETECTED',r['shorts'])
PY
echo 'PHY_PG_DECLARED_GEOMETRY_FIXTURE_AND_MUTANTS_PASS; ASSUMED PHY ONLY; NO FOUNDRY CLAIM'
