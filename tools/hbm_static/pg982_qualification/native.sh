#!/bin/bash
set -euo pipefail
ROOT=${PG982_RUN_ROOT:?PG982_RUN_ROOT must name immutable staged run root}
cd "$ROOT/src"
export SRC="$ROOT/src" OT_ORFS_CORNER_OVERRIDE=TC OT_THREADS=4
export OT_CTS_FIX_HOOKS='physical/common_flow/cg_pushdown.tcl physical/common_flow/clk_net_protect.tcl physical/common_flow/link_budget_hook.tcl'
mkdir -p "$ROOT/native982"
set +e
HM=0.03 bash tools/ref_tile/ref_route.sh tools/hbm_static/pg982_qualification/native.env pg982_synth_native "$ROOT/native982" floorplan > "$ROOT/native982/launcher.log" 2>&1
flow_rc=$?
set -e
printf '%s\n' "$flow_rc" > "$ROOT/native982/launcher.rc"
# Intentional early exit after canonical mapped census means floorplan metrics do not exist.
# Preserve that wrapper verdict; only a real canonical native receipt can satisfy this recipe.
grep -Rq 'PG982_NATIVE_ONLY_DONE_NO_LAYOUT' "$ROOT/native982/pg982_synth_native/work/orfs/logs"
python3 - "$ROOT/native982/pg982_synth_native/work/orfs/native_census.json" <<'CHECK'
import json,sys
p=sys.argv[1];d=json.load(open(p))
assert d['schema']=='opentallas.pre_gate_native_census.v1'
assert d['top']=='ot_hbm_su_pgrg_pair'
assert d['status']=='PASS' and d['max_dynamic_loads']<=32
assert not d.get('role_errors') and not d.get('violations')
print('PG982_ACTUAL_NATIVE_RECEIPT',p,'max',d['max_dynamic_loads'])
CHECK
