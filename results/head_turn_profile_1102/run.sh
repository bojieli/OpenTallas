#!/bin/bash
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
python3 - "$D" <<'PY'
import json,hashlib,sys
from pathlib import Path
D=Path(sys.argv[1]);m=json.load(open(D/'MANIFEST.json'));v=json.load(open(D/'A_LOOK_RELEASE.json'))
assert v['personally_viewed'] is True
assert v['source']['hd_st_n3_turn']==m['source_inputs']
for f,h in m['source_inputs'].items():assert hashlib.sha256((D/'kit'/f).read_bytes()).hexdigest()==h,(f,h)
assert hashlib.sha256((D/'kit/postcts_gate_profile.tcl').read_bytes()).hexdigest()==m['private_profile_sha256']
assert not list((D/'kit').glob('B_query_*.log')),'refuse duplicate native producer/output'
PY
for c in TT FF; do
 docker run --rm --cpus 2 --memory 8g --memory-swap 8g -v "$D/kit":/work -v "$D/kit/native":/work/native:ro -e OT_POSTCTS_GRT=1 -e OT_CORNER="$c" -e ODB=/work/native/5_1_grt.odb -e OT_POSTCTS_REAL_CLOCK_PROFILE=1 -e OT_POSTCTS_BINDING_TOL=0 openroad/orfs:asap7lock bash -lc 'set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /work/verify_context.py; openroad -threads 2 -exit /work/path_query_B.tcl' > "$D/kit/B_query_$c.log" 2>&1
done
echo 'ONE Turn readonly profileB TT/FF COMPLETE; no gate rejudge, repair, route or adoption'
