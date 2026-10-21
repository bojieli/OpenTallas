#!/bin/bash
set -euo pipefail
TASK_NATIVE_ROOT="$PWD"
cd src
python3 - <<'PY'
import json,hashlib
from pathlib import Path
p=Path('tools/ref_tile/native_census.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='4e7a7a425a8669a5f586ed3aa2873038e727293a9128aabae360fcbaa2cd61e0'
d=json.load(open('physical/ref_tile/hbm_hcq_hub_c7p40/spec.json'))
for k,v in dict(SAFE=2,RD_CAPTURE=39,GATHER_PHASE=39,GATHER_PERIOD=40,DONE_LAT=35,DRLY=2,CHX=11).items():assert d['params'][k]==v,(k,d['params'])
print('P40_NATIVE_SOURCE_PUBLISHED_AUTHORITY_MATCH')
PY
printf '%s\n' 453f3acef > SOURCE_COMMIT
export SRC="$PWD" SYNTH_TIMEOUT=unlimited OT_ORFS_CORNER_OVERRIDE=TC
bash tools/ref_tile/ref_route.sh physical/ref_tile/hbm_hcq_hub_c7p40/kit.env native "$TASK_NATIVE_ROOT/native_out" floorplan --native-census
