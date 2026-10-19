#!/bin/bash
# S81-DIEPLACE GEN candidate (opt-in): reset-space + 8 SerDes 518.4x3844.8 slots (W/E reserve 256.55, approved candidate)
# + legal reset tree (OT_RESET_LEGAL) -> strict bind -> physical case -> GRT/STA.  PILOT_NOT_A_GATE until the landing
# pilot re-derives E/K for the changed lanes (lane_age_delta.json).
# usage: run_gen.sh <DIR with src/> <SOURCE_SHA> <MAIN_SHA>
set -euo pipefail
D=${1:?dir}; SOURCE_SHA=${2:?source sha}; MAIN_SHA=${3:?main sha}
cd "$D/src"
export OT_GIT_DIR=${OT_GIT_DIR:-/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git}
BASE=results/arch/s81_dv_1016
TABLE=$BASE/bind/bind_table_p4l3_mu.json; LAND=$BASE/landing/p4l3/land_plan.json
python3 tools/s81_dv/dv_plan.py --layout p4 --p4l --mu 1 --tier-w 276 --lanes 4 --p4h-drop 6 --frame-w 1436.832 --pathfix --placefix --reset-space --lk-slots "$BASE/p4l_lkcol/plan.json" --out "$D/plan_rs" > "$D/plan.log" 2>&1
python3 tools/s81_dv/serdes_slot_candidate.py --plan "$D/plan_rs/plan.json" --out "$D/plan" --reticle-reserve-um 256.55 >> "$D/plan.log" 2>&1
python3 - "$D/plan/plan.json" "$BASE/dieplace_gen_1019/plan.json" <<'PY'
import json,sys
a,b=(json.load(open(p)) for p in sys.argv[1:])
assert a['blocks']==b['blocks'] and a['links']==b['links'], 'regenerated plan != committed candidate plan'
print('PLAN_MATCHES_COMMITTED')
PY
python3 "$BASE/bind/mk_table_p4l3_mu.py" > "$D/table.log" 2>&1
python3 - <<'PREFLIGHT'
import json
from pathlib import Path
T=json.load(open('results/arch/s81_dv_1016/bind/bind_table_p4l3_mu.json'))
missing=[f for f in T.get('rtl_files',[]) if not Path(f).is_file()]
if missing: raise SystemExit('SOURCE_PREFLIGHT_FAIL '+repr(missing))
print('SOURCE_PREFLIGHT_PASS',len(T.get('rtl_files',[])))
PREFLIGHT
# pass 1: netlist only (default reset tree) -> the exact obstacle set reset bodies must avoid
OT_BIND_EMIT_ONLY=1 python3 tools/s81_dv/dv_diecase.py --plan "$D/plan/plan.json" --out "$D/pass1" --bind real --bind-table "$TABLE" --land-plan "$LAND" > "$D/pass1.log" 2>&1
python3 tools/s81_dv/dv_rvcase.py --plan "$D/plan/plan.json" --bind-dir "$D/pass1/bind" --bind-table "$TABLE" --land-plan "$LAND" --out "$D/obst_case" --view-refs "$SOURCE_SHA" "$MAIN_SHA" --dump-obstacles "$D/obstacles.json" > "$D/obstacles.log" 2>&1
echo OBSTACLES_DONE
# pass 2: legal reset tree + STRICT bind
OT_RESET_LEGAL="$D/obstacles.json" python3 tools/s81_dv/dv_diecase.py --plan "$D/plan/plan.json" --out "$D/bound" --bind real --bind-table "$TABLE" --land-plan "$LAND" > "$D/bind.log" 2>&1
echo STRICT_BIND_DONE
python3 tools/s81_dv/dv_rvcase.py --plan "$D/plan/plan.json" --bind-dir "$D/bound/bind" --bind-table "$TABLE" --land-plan "$LAND" --out "$D/case" --view-refs "$SOURCE_SHA" "$MAIN_SHA" --die-repair --dieflow-ref "$SOURCE_SHA" --corners tt ff ss > "$D/case_gen.log" 2>&1
python3 - "$D" <<'PY'
import json,sys
from pathlib import Path
c=Path(sys.argv[1])/'case'/'case.json'; q=json.loads(c.read_text())
q['label']='PILOT_NOT_A_GATE: S81-DIEPLACE GEN candidate; 20 changed lane ages, land plan E/K stale for them (lane_age_delta.json)'
c.write_text(json.dumps(q,indent=1))
PY
date > "$D/gen.done"
CPUS=16 MEMG_GRT=96 MEMG_STA=64 bash "$D/case/run_all.sh" > "$D/chain.log" 2>&1
echo CHAIN_DONE
