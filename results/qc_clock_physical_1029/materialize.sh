#!/bin/bash
# Run this through ot-run; only materializes a reviewed jointly reserved plan.
set -euo pipefail
if [[ $# != 5 ]]; then echo 'usage: materialize.sh PREBUILD_DIR SOURCE_ODB POWER_ACCESS_JSON POWER_ACCESS_TCL OUT_DIR' >&2; exit 2; fi
P=$(realpath "$1"); I=$(realpath "$2"); A=$(realpath "$3"); T=$(realpath "$4")
mkdir -p "$5"; O=$(realpath "$5"); S=$(cd "$(dirname "$0")" && pwd)
python3 - "$P" "$A" <<'PY'
import hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1]); r=json.loads((p/'prebuild.json').read_text())
assert r['status']=='PASS_PREBUILD', 'geometry prebuild has not passed'
a=r.get('power_access_reservation',{})
assert a.get('rectangles',0)>0, 'actual power access was not jointly reserved'
assert a['sha256']==hashlib.sha256(Path(sys.argv[2]).read_bytes()).hexdigest(), 'power access geometry differs from clock reservation'
for f in ('fixed_pg.tcl','fixed_clock_only.tcl','review_region.png'):
 assert (p/f).is_file(), f+' missing'
PY
# The caller must VIEW/review the jointly-reserved render before this action.
docker run --rm --name "codex-qc-fixed-clock-$$" --memory=24g --memory-swap=24g --cpus=4 \
 -v "$I:/i/clock_grafted.odb:ro" -v "$P:/p:ro" -v "$T:/a/power_access.tcl:ro" \
 -v "$S:/s:ro" -v "$O:/o" openroad/orfs:asap7lock bash -lc \
 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /s/materialize.tcl > /o/materialize.log 2>&1; rc=$?; chown -R 1000:1000 /o; exit $rc'
grep -q OT_CLOCK_MATERIALIZED "$O/materialize.log"
