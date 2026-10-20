#!/bin/bash
# S81-DIECHAIN 10-19: GEN mu4 (claude/s81-diechain-mu4-1019 8179ff99b = mu3 ceaed19c4 + corridor repeaters + 405 odb census) on plan p4l_lkcol_mu_pf
# strict bind (binder-of-record checker) -> main-checker strict (unread/open census, non-fatal) -> real-view case -> GRT/STA chain
set -uo pipefail
D=$(cd "$(dirname "$0")" && pwd)
SRC_SHA=${1:?source sha}; MAIN_SHA=${2:?main sha}
export OT_GIT_DIR=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
BASE=results/arch/s81_dv_1016
PLAN=$BASE/p4l_lkcol_mu_pf/plan.json
TBL=$BASE/bind/bind_table_p4l3_mu.json
LP=$BASE/landing/p4l3/land_plan.json
cd "$D/src" || exit 2
python3 tools/s81_dv/dv_diecase.py --plan "$PLAN" --out "$D/bind_mu4" --bind real --bind-table "$TBL" --land-plan "$LP" > "$D/bind_mu4.log" 2>&1
echo "BIND_RC $?" >> "$D/steps.log"
grep -q "DIE_PORT_BIND PASS" "$D/bind_mu4/bind/port_bind.log" || { echo "BIND_STRICT_FAIL" >> "$D/steps.log"; exit 3; }
# main checker (unread / OUTPUT_OPEN census) in a sibling copy, same args
rm -rf "$D/srcm"; cp -a "$D/src" "$D/srcm"; cp "$D/die_port_bind_main.py" "$D/srcm/tools/die_port_bind.py"
(cd "$D/srcm" && python3 tools/s81_dv/dv_diecase.py --plan "$PLAN" --out "$D/bind_mu4_mainchk" --bind real --bind-table "$TBL" --land-plan "$LP" > "$D/bind_mu4_mainchk.log" 2>&1; echo "MAINCHK_RC $?" >> "$D/steps.log") &
MC=$!
python3 tools/s81_dv/dv_rvcase.py --plan "$PLAN" --bind-dir "$D/bind_mu4/bind" --bind-table "$TBL" --land-plan "$LP" --out "$D/case_mu4" \
  --view-refs "$SRC_SHA" "$MAIN_SHA" --die-repair --dieflow-ref "$SRC_SHA" --corners tt ff ss > "$D/case_gen.log" 2>&1
RC=$?; echo "CASE_RC $RC" >> "$D/steps.log"
wait $MC
[ $RC -eq 0 ] || exit $RC
python3 - "$D" <<'PY'
import json,sys
from pathlib import Path
f=Path(sys.argv[1])/'case_mu4'/'case.json'; q=json.loads(f.read_text())
q['label']='PILOT_NOT_A_GATE mu4: '+q.get('label','')
f.write_text(json.dumps(q,indent=1))
PY
date > "$D/gen.done"
CPUS=16 MEMG_GRT=96 MEMG_STA=64 bash "$D/case_mu4/run_all.sh" > "$D/chain.log" 2>&1
echo "CHAIN_RC $?" >> "$D/steps.log"
