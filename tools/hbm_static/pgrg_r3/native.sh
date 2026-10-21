#!/bin/bash
# HBM-OWN/PHY-PG 10-21: pre-gate native census of the r3 pair (d4p kit; d4p_fb has the same RTL), canonical
# tools/ref_tile/native_census.tcl hook before floorplan, no layout (adapted from pg982_qualification/native.sh).
set -euo pipefail
ROOT=${PGRG_R3_ROOT:?run root with src/}
cd "$ROOT/src"
export SRC="$ROOT/src" OT_ORFS_CORNER_OVERRIDE=TC OT_THREADS=4
export OT_CTS_FIX_HOOKS='physical/common_flow/cg_pushdown.tcl physical/common_flow/clk_net_protect.tcl physical/common_flow/link_budget_hook.tcl'
mkdir -p "$ROOT/native"
set +e
HM=0.03 bash tools/ref_tile/ref_route.sh tools/hbm_static/pgrg_r3/native.env pgrg_r3_native "$ROOT/native" floorplan > "$ROOT/native/launcher.log" 2>&1
echo $? > "$ROOT/native/launcher.rc"
set -e
grep -Rq 'PG982_NATIVE_ONLY_DONE_NO_LAYOUT' "$ROOT/native/pgrg_r3_native/work/orfs/logs"
python3 - "$ROOT/native/pgrg_r3_native/work/orfs/native_census.json" <<'CHECK'
import json,sys
p=sys.argv[1];d=json.load(open(p))
assert d['top']=='ot_hbm_su_pgrg_pair'
print('PGRG_R3_NATIVE',d['status'],'max',d.get('max_dynamic_loads'),'viol',len(d.get('violations') or []),'role_err',len(d.get('role_errors') or []))
assert d['status']=='PASS' and d['max_dynamic_loads']<=32 and not d.get('role_errors') and not d.get('violations')
CHECK
