#!/bin/bash
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd);K=$D/kit
python3 - "$K" <<'PY'
from pathlib import Path
import json,hashlib,sys
k=Path(sys.argv[1]);r=json.load(open(k/'dpl_only_receipt.json'))
for p in r['unchanged_inputs']:assert hashlib.sha256((k/p['relative']).read_bytes()).hexdigest()==p['sha256'],p['relative']
for n,h in r['geometry'].items():assert hashlib.sha256((k/n).read_bytes()).hexdigest()==h,n
assert r['normal_targets']==['do-3_5_place_dp','do-3_place'] and r['FF_count']==18768 and r['moved_FF_count']==70
assert json.load(open(k/'lec/lec.json'))['verdict']=='EQUIVALENT'
print('DPL_ONLY_SOURCE_POSE_GUARD_PASS',len(r['unchanged_inputs']))
PY
DK=docker;docker ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --name "codex-ctl-dpl-only-$$" --cpus 2 --memory 8g --memory-swap 8g -v "$K":/work -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=2 do-3_5_place_dp do-3_place
chown -R "$HUID:$HGID" /work/run
' > "$D/dpl.log" 2>&1
python3 - "$K" <<'PY'
from pathlib import Path
import json,hashlib,sys
k=Path(sys.argv[1]);r=json.load(open(k/'dpl_only_receipt.json'))
for p in r['unchanged_inputs']:assert hashlib.sha256((k/p['relative']).read_bytes()).hexdigest()==p['sha256'],p['relative']
b=list((k/'run/results/asap7').glob('*/base'));assert len(b)==1 and (b[0]/'3_place.odb').is_file() and (b[0]/'3_place.sdc').is_file() and not (b[0]/'4_cts.odb').exists()
print('DPL_ONLY_COMPLETE_SOURCE_UNCHANGED',b[0]/'3_place.odb')
PY
