#!/bin/bash
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
SOURCE_SHA=${1:?source commit required}
MAIN_SHA=${2:?fallback main commit required}
cd "$D/src"
export OT_GIT_DIR=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
BASE=results/arch/s81_dv_1016
python3 tools/s81_dv/dv_plan.py --layout p4 --p4l --tier-w 276 --lanes 4 --p4h-drop 6 --frame-w 1436.832 --lk-slots "$BASE/p4l_lkcol/plan.json" --mu 1 --pathfix --placefix --out "$D/plan" > "$D/plan.log" 2>&1
python3 "$BASE/bind/mk_table_p4l3_mu.py" > "$D/table.log" 2>&1
python3 - <<'PREFLIGHT'
import json
from pathlib import Path
T=json.load(open('results/arch/s81_dv_1016/bind/bind_table_p4l3_mu.json'))
missing=[f for f in T.get('rtl_files',[]) if not Path(f).is_file()]
if missing: raise SystemExit('SOURCE_PREFLIGHT_FAIL '+repr(missing))
print('SOURCE_PREFLIGHT_PASS',len(T.get('rtl_files',[])))
PREFLIGHT
python3 tools/s81_dv/dv_diecase.py --plan "$D/plan/plan.json" --out "$D/bound_v2" --bind real --bind-table "$BASE/bind/bind_table_p4l3_mu.json" --land-plan "$BASE/landing/p4l3/land_plan.json" > "$D/bind.log" 2>&1
python3 tools/s81_dv/dv_rvcase.py --plan "$D/plan/plan.json" --bind-dir "$D/bound_v2/bind" --bind-table "$BASE/bind/bind_table_p4l3_mu.json" --land-plan "$BASE/landing/p4l3/land_plan.json" --out "$D/case_v2" --view-refs "$SOURCE_SHA" "$MAIN_SHA" --die-repair --dieflow-ref "$SOURCE_SHA" --corners tt ff ss > "$D/case_gen.log" 2>&1
python3 - "$D" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]); c=p/'case_v2'
f=c/'case.json'; q=json.loads(f.read_text());q['label']='PILOT_NOT_A_GATE: changed station ages, old landing calendar; physical-placement replay only';f.write_text(json.dumps(q,indent=1))
PY
date > "$D/gen.done"
CPUS=16 MEMG_GRT=96 MEMG_STA=64 bash "$D/case_v2/run_all.sh" > "$D/chain.log" 2>&1
