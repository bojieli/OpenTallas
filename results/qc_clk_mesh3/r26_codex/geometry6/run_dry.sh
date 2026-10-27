#!/bin/bash
set -euo pipefail
cd /work
python3 - <<'PY'
import gzip,shutil
from pathlib import Path
p=Path('inputs')
for name in ('clock_spec','plan'):
 with gzip.open(p/(name+'.json.gz'),'rb') as a,open(p/(name+'.json'),'wb') as b:shutil.copyfileobj(a,b)
PY
python3 /src/tools/die_plan/die_clock_mesh.py build inputs/plan.json --explicit-cells inputs/clock_spec.json --ndr 16w --libdir /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM --out build7 > build7.log 2>&1
printf 'QC_CLOCK_DRY7_DONE\n'
