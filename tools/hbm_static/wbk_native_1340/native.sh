#!/bin/bash
set -euo pipefail
ROOT=${WBK1340_RUN_ROOT:?immutable staged root}
cd "$ROOT/src"
export SRC="$ROOT/src" OT_ORFS_CORNER_OVERRIDE=TC OT_THREADS=8
mkdir -p "$ROOT/native"
python3 tools/ref_tile/ref_tile.py gen tools/hbm_static/wbk_native_1340/spec.json --commit "$(cat SOURCE_COMMIT)" > "$ROOT/native/gen.log" 2>&1
set +e
HM=0.03 bash tools/ref_tile/ref_route.sh tools/hbm_static/wbk_native_1340/native.env wbk1340_synth_native "$ROOT/native" floorplan > "$ROOT/native/launcher.log" 2>&1
flow_rc=$?
set -e
printf '%s\n' "$flow_rc" > "$ROOT/native/launcher.rc"
# An intentional pre-floorplan exit does not supply layout metrics. Preserve the
# wrapper rc and inspect only actual canonical native receipt + no-layout marker.
grep -Rq 'WBK1340_NATIVE_ONLY_DONE_NO_LAYOUT' "$ROOT/native/wbk1340_synth_native/work/orfs/logs"
python3 - "$ROOT/native/wbk1340_synth_native/work/orfs/native_census.json" <<'PY'
import json,sys
j=json.load(open(sys.argv[1]))
print('WBK1340_ACTUAL_NATIVE',j['status'],'roots',j['roots_examined'],'max',j['max_dynamic_loads'],'violations',len(j['violations']))
assert j['schema']=='opentallas.pre_gate_native_census.v1' and j['top']=='ot_hbm_svc_wb_kport_q'
assert j['status']=='PASS' and j['max_dynamic_loads']<=32 and not j['role_errors'] and not j['violations']
PY
