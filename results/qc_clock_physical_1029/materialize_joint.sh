#!/bin/bash
# Caller must personally VIEW/review the final jointly reserved prebuild first.
# Use ot-run; no PG coupon TCL is sourced, so no intermediate read_db can reset
# an already emitted canonical grid or clock wire.
set -euo pipefail
if [[ $# -lt 8 || $# -gt 9 ]]; then
 echo 'usage: materialize_joint.sh PREBUILD SOURCE_ODB CLOCK_ACCESS_PLAN RESERVED_POWER_JSON NATIVE_HELPER DIRECT_PLAN BRIDGE_PLAN OUT [MEM_GB]' >&2; exit 2
fi
P=$(realpath "$1"); I=$(realpath "$2"); A=$(realpath "$3"); R=$(realpath "$4"); H=$(realpath "$5"); D=$(realpath "$6"); B=$(realpath "$7")
mkdir -p "$8"; O=$(realpath "$8"); M=${9:-48}; S=$(cd "$(dirname "$0")" && pwd); W=$(realpath "$S/../..")
python3 - "$P" "$A" "$R" "$O" "$B" <<'PY'
import hashlib,json,sys
from collections import Counter
from pathlib import Path
p,a,r,o,b=map(Path,sys.argv[1:]);pre=json.load(open(p/'prebuild.json'));access=json.load(open(a/'access_plan.json'))
assert pre['status']=='PASS_PREBUILD','No passing jointly reserved fixed-wire prebuild'
assert pre['power_access_reservation']['sha256']==hashlib.sha256(r.read_bytes()).hexdigest(),'Power geometry differs from reviewed clock reservation'
assert not access['failed'] and sum(len(q['members']) for q in access['paths'])==89180,'Clock-cell power incomplete'
assert 'tech_vias_dbu' in access,'Missing actual via geometry contract'
raw=(a/'reserved_access.json').read_bytes().strip();combined=r.read_bytes().strip();bridges=json.load(open(b))
if combined==raw:tail=[]
else:
 assert raw.endswith(b']') and combined.startswith(raw[:-1]+b','),'Combined reservation must retain exact clock-cell PG array prefix'
 tail=json.loads(b'['+combined[len(raw):])
expected=Counter((q['net'],'M8',*[v/bridges['dbu'] for v in q['m8_dbu']]) for q in bridges['paths'])
assert Counter(map(tuple,tail))==expected,'Native bridge geometry differs from clock reservation'
for f in ('fixed_pg.tcl','fixed_clock_only.tcl','pg_rects.json','review_region.png'):assert (p/f).is_file(),f+' missing'
for f in ('clock_raw.odb','clock_cell_power.odb','clock_power.odb'):assert not (o/f).exists(),'Use a new output directory; preserve existing '+f
PY
sudo docker run --rm --name "codex-qc-joint-materialize-$$" --memory="${M}g" --memory-swap="${M}g" --cpus=4 \
 -v "$I:/input/source.odb:ro" -v "$P:/prebuild:ro" -v "$A:/access:ro" \
 -v "$H:/native/apply_joins.py:ro" -v "$D:/native/direct.json:ro" -v "$B:/native/bridges.json:ro" \
 -v "$W:/work:ro" -v "$O:/out" openroad/orfs:asap7lock bash -lc '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
trap "chown -R 1000:1000 /out" EXIT
openroad -no_init -exit /work/results/qc_clock_physical_1029/materialize_joint.tcl > /out/clock_grid.log 2>&1
openroad -python -exit /work/results/qc_pg_access_1029/apply_access.py --odb /out/clock_raw.odb --plan /access --grid /prebuild/pg_rects.json --out /out/clock_cell_power.odb > /out/clock_cell_power.log 2>&1
openroad -python -exit /native/apply_joins.py --source /out/clock_cell_power.odb --direct-plan /native/direct.json --bridge-plan /native/bridges.json --output /out/clock_power.odb --receipt /out/native_pg.json > /out/native_pg.log 2>&1
'
python3 - "$O" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]);a=json.load(open(p/'clock_cell_power.access.json'));b=json.load(open(p/'native_pg.json'))
assert a['contacts']==89180 and a['non_pg_before_sha256']==a['non_pg_after_sha256']
assert b['clock_and_signal_wire_sha_before']==b['clock_and_signal_wire_sha_after']
assert b['instances_sha_before']==b['instances_sha_after']
print('OT_CLOCK_POWER_MATERIALIZED clock_contacts=89180 native_supply_terms='+str(b['unique_supply_terms']))
print('NOT_SIGNED: actual full-wire connectivity/DRC/extraction/duty/reset/signals/IR and die gates remain required')
PY
