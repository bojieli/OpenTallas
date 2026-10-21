#!/bin/bash
# HBM-OWN/SU-PGLG 10-21: pre-gate native census of the d4h pair (synthesis + canonical native_census.tcl, no layout).
# Same recipe as tools/hbm_static/pg982_qualification/native.sh (Codex), pointed at the d4h kit.
set -euo pipefail
ROOT=${PGD4H_RUN_ROOT:?PGD4H_RUN_ROOT must name the staged run root}
cd "$ROOT/src"
export SRC="$ROOT/src" OT_ORFS_CORNER_OVERRIDE=TC OT_THREADS=4
export OT_CTS_FIX_HOOKS='physical/common_flow/cg_pushdown.tcl physical/common_flow/clk_net_protect.tcl physical/common_flow/link_budget_hook.tcl'
mkdir -p "$ROOT/native"
set +e
HM=0.03 bash tools/ref_tile/ref_route.sh tools/hbm_static/pg_d4h_qualification/native.env pgd4h_synth_native "$ROOT/native" floorplan > "$ROOT/native/launcher.log" 2>&1
echo $? > "$ROOT/native/launcher.rc"
set -e
grep -Rq 'PGD4H_NATIVE_ONLY_DONE_NO_LAYOUT' "$ROOT/native/pgd4h_synth_native/work/orfs/logs"
python3 - "$ROOT/native/pgd4h_synth_native/work/orfs/native_census.json" <<'CHECK'
import json,sys
p=sys.argv[1];d=json.load(open(p))
assert d['top']=='ot_hbm_su_pgrg_pair'
print('PGD4H_NATIVE', d['status'], 'max', d['max_dynamic_loads'], 'viol', len(d.get('violations') or []), 'role_err', len(d.get('role_errors') or []), p)
assert d['status']=='PASS' and d['max_dynamic_loads']<=32
CHECK
