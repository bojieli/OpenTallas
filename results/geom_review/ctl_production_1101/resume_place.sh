#!/bin/bash
# One reviewed geometry-only successor from immutable qualified native SYNTH.
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
K=$D/kit
python3 - "$K" <<'PY'
import hashlib,json,sys
from pathlib import Path
k=Path(sys.argv[1]);receipt=json.load(open(k/'place_source_receipt.json'))
for row in receipt['unchanged_inputs']:
 p=k/row['relative'];assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],str(p)
assert receipt['scope']=='ONE PLACE only; no GEN/SYNTH/LEC/CTS/GRT/route/STA'
assert json.load(open(k/'lec/lec.json')).get('verdict') in ('EQUIVALENT','PASS'), 'actual LEC verdict absent'
print('CTL_PLACE_SOURCE_GUARD_PASS',len(receipt['unchanged_inputs']))
PY
DK=docker;docker ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --name "codex-ctl-place-$$" --cpus 8 --memory 32g --memory-swap 32g -v "$K":/work -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8"
# Dependency-free ordinary ORFS stages, as KW-RESUME-1: consume existing 1_synth.odb.
$M do-floorplan
$M do-place
chown -R "$HUID:$HGID" /work/run
' > "$D/place.log" 2>&1
python3 - "$K" <<'PY'
import hashlib,json,sys
from pathlib import Path
k=Path(sys.argv[1]);receipt=json.load(open(k/'place_source_receipt.json'))
for row in receipt['unchanged_inputs']:
 assert hashlib.sha256((k/row['relative']).read_bytes()).hexdigest()==row['sha256'],row['relative']
bases=list((k/'run/results/asap7').glob('*/base'));assert len(bases)==1
assert (bases[0]/'3_place.odb').is_file() and (bases[0]/'3_place.sdc').is_file()
assert not (bases[0]/'4_cts.odb').exists()
print('CTL_PLACE_ONLY_COMPLETE',bases[0]/'3_place.odb')
PY
