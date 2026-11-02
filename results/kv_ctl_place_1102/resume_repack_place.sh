#!/bin/bash
# Dispatch only after ROOT's independent LOOK and scoped successor ruling.
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd);K=$D/kit
python3 - "$K" <<'PY'
import json,hashlib,sys
from pathlib import Path
k=Path(sys.argv[1]);r=json.load(open(k/'repack_source_receipt.json'))
for q in r['unchanged_inputs']:
 assert hashlib.sha256((k/q['relative']).read_bytes()).hexdigest()==q['sha256'],q['relative']
for name,sha in r['geometry'].items():assert hashlib.sha256((k/name).read_bytes()).hexdigest()==sha,name
assert r['source_cycles_delta']==r['R8_delta']==0 and r['FF_inventory']==18768
assert json.load(open(k/'lec/lec.json'))['verdict']=='EQUIVALENT'
print('REPACK_SOURCE_FP_GUARD_PASS',len(r['unchanged_inputs']))
PY
DK=docker;docker ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --name "codex-ctl-repack-place-$$" --cpus 8 --memory 32g --memory-swap 32g -v "$K":/work -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-place
chown -R "$HUID:$HGID" /work/run
' > "$D/place.log" 2>&1
python3 - "$K" <<'PY'
import json,hashlib,sys
from pathlib import Path
k=Path(sys.argv[1]);r=json.load(open(k/'repack_source_receipt.json'))
for q in r['unchanged_inputs']:assert hashlib.sha256((k/q['relative']).read_bytes()).hexdigest()==q['sha256'],q['relative']
b=list((k/'run/results/asap7').glob('*/base'));assert len(b)==1 and (b[0]/'3_place.odb').is_file() and not (b[0]/'4_cts.odb').exists()
print('REPACK_PLACE_ONLY_COMPLETE',b[0]/'3_place.odb')
PY
