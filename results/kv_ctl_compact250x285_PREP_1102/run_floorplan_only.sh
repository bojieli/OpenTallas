#!/bin/bash
# Dispatch only after independent actual-GEN image review and scoped FP-only approval.
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd);K=$D/kit
python3 - "$K" <<'PY'
import json,hashlib,sys
from pathlib import Path
k=Path(sys.argv[1]);r=json.load(open(k/'floorplan_source_receipt.json'));assert r['scope']=='ONE native do-floorplan only; no GEN/SYNTH/LEC/PLACE/CTS/GRT';assert r['retained_subject_join']['status']=='SOURCE_IDENTITY_MATCHED'
for p,h in r['unchanged_input_sha256'].items():assert hashlib.sha256((k/p).read_bytes()).hexdigest()==h,p
assert not list((k/'run/results').rglob('2_floorplan.odb'))
print('FP_ONLY_GENUINE_STAGE1_SOURCE_GUARD_PASS',len(r['unchanged_input_sha256']))
PY
DK=docker;docker ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --name "codex-ctl-compact-fp-$$" --cpus 2 --memory 8g --memory-swap 8g -v "$K":/work -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=2 -n do-floorplan > /work/fp_dry_target.log
python3 /work/guard_fp_target.py /work/fp_dry_target.log
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=2 do-floorplan
chown -R "$HUID:$HGID" /work/run
' > "$D/floorplan.log" 2>&1
python3 - "$K" <<'PY'
import json,hashlib,sys
from pathlib import Path
k=Path(sys.argv[1]);r=json.load(open(k/'floorplan_source_receipt.json'))
for p,h in r['unchanged_input_sha256'].items():assert hashlib.sha256((k/p).read_bytes()).hexdigest()==h,p
assert len(list((k/'run/results').rglob('2_floorplan.odb')))==1 and not list((k/'run/results').rglob('3_place.odb')) and not list((k/'run/results').rglob('4_cts.odb'))
print('FP_ONLY_COMPLETE_SOURCE_STAGE1_UNCHANGED_NO_PLACE')
PY
