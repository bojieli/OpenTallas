#!/bin/bash
set -uo pipefail
D=$(pwd)
export OT_GIT_DIR=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
SRC=804d68ef69adab4aca463317d74bbed100da330d
if [ ! -f src/.source_ready ]; then
 mkdir -p src
 git --git-dir="$OT_GIT_DIR" archive "$SRC" tools rtl results/arch/s81_dv_1016 physical/rom_host_ingest | tar -xf - -C src || exit 2
 printf '%s\n' "$SRC" > src/.source_ready
fi
cd src || exit 2
args=(--layout p4 --tier-w 276 --lanes 4 --p4l --p4h-drop 6 --frame-w 1436.832 --mu 1 --pathfix --lk-slots results/arch/s81_dv_1016/p4l_lkcol/plan.json --revision dv-p4l-mu1-realctrl)
cp tools/s81_dv/dv_plan.py "$D/dv_plan_original.py"
python3 tools/s81_dv/dv_plan.py "${args[@]}" --out "$D/plan_baseline" > "$D/plan_baseline.log" 2>&1; echo BASE_PLAN_RC=$?
cp "$D/dv_plan_next.py" tools/s81_dv/dv_plan.py
python3 tools/s81_dv/dv_plan.py "${args[@]}" --out "$D/plan_default" > "$D/plan_default.log" 2>&1; echo DEFAULT_PLAN_RC=$?
cmp "$D/plan_baseline/plan.json" "$D/plan_default/plan.json"; echo DEFAULT_IDENTITY_RC=$?
python3 tools/s81_dv/dv_plan.py "${args[@]}" --ctrl-view-size 388.8 324 --array-y-shift 86.4 --out "$D/plan_realctrl" > "$D/plan_realctrl.log" 2>&1; plan_rc=$?; echo REALCTRL_PLAN_RC=$plan_rc
[ "$plan_rc" -eq 0 ] || exit "$plan_rc"
python3 tools/s81_dv/dv_diecase.py --plan "$D/plan_realctrl/plan.json" --out "$D/bind_realctrl" --bind real --bind-table results/arch/s81_dv_1016/bind/bind_table_p4l3_mu.json --land-plan results/arch/s81_dv_1016/landing/p4l3/land_plan.json > "$D/bind_realctrl.log" 2>&1; echo BIND_RC=$?
python3 - "$D" <<'PY2'
import json,sys
from pathlib import Path
p=Path(sys.argv[1])/'bind_realctrl/bind/port_bind.json'
if not p.exists(): print('NO_PORT_REPORT');raise SystemExit(3)
x=json.loads(p.read_text());print(x['verdict']);print(x['summary']);raise SystemExit(0 if x['verdict']=='PASS' else 4)
PY2
