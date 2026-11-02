#!/bin/bash
# PREPARED ONLY. Invoke via ot-run after source/manifest review; no implicit make targets.
set -euo pipefail
[ "$#" = 2 ] || { echo 'usage: run_candidate.sh place|route REVIEWED_MANIFEST_SHA256'; exit 2; }
PHASE=$1
[ "$PHASE" = place ] || [ "$PHASE" = route ] || exit 2
[ "$(sha256sum candidate_manifest.json | cut -d' ' -f1)" = "$2" ] || exit 2
export CANDIDATE_PHASE="$PHASE"
export REVIEWED_PLACEMENT_SHA256=''
if [ "$PHASE" = route ]; then
 export REVIEWED_PLACEMENT_SHA256=$(python3 -c 'import json;d=json.load(open("placement_review.json"));assert d["scope"]=="L1_THREE_DATA_EDITS_ROUTE";print(d["placement_sha256"])')
fi
python3 - <<'PY'
import hashlib,json
from pathlib import Path
r=json.load(open('candidate_protected.json'))
for n,h in r['files'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n
assert hashlib.sha256(Path('snapshot/5_1_grt.odb').read_bytes()).hexdigest()==r['source_5_1_odb_sha256']
assert hashlib.sha256(Path('snapshot/4_cts.sdc').read_bytes()).hexdigest()==r['source_final_sdc_sha256']
PY
docker run --rm --cpus 2 --memory 16g --memory-swap 16g -v "$PWD":/work -w /work -e CANDIDATE_PHASE -e REVIEWED_PLACEMENT_SHA256 -e OT_GEOM_OUT=/work/candidate_place_geom.tsv openroad/orfs:asap7lock bash -lc 'set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/load_candidate.tcl; if [ "$CANDIDATE_PHASE" = route ]; then grep -Fx CANDIDATE_THREE_DATA_EDITS_COMPLETE /work/candidate_route.log; openroad -exit /work/combined_post.tcl > /work/combined_post.log 2>&1; fi' > "candidate_${PHASE}.log" 2>&1
if [ "$PHASE" = place ]; then
 grep -Fx CANDIDATE_PLACE_COUPON_COMPLETE candidate_place.log
 echo 'STOP: actual candidate placement LOOK required before a distinct route invocation.'
 exit 0
fi
grep -Fx CANDIDATE_THREE_DATA_EDITS_COMPLETE candidate_route.log
python3 guide_coverage.py
# Complete current signoff/helper bundle required; this read-only policy consumer performs no repair.
docker run --rm --cpus 2 --memory 16g --memory-swap 16g -v "$PWD":/work -w /work openroad/orfs:asap7lock bash -lc 'set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /work/legacy_gate.py /work grt' > candidate_policy.log 2>&1
