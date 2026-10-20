#!/bin/bash
# S81-DIE10 10-20: CORRECTED mu6 die chain (replaces ROOT-held DIE9 waiter 3852152 / run_mu6.sh chain).
# Fixes vs the frozen recipe: (1) dv_rvcase on source claude/s81-die10-1020 carries --macro-views (13337f0ae; 1b7's tool
# lacked it -> argparse refuse) and the native consumer (09bc694a1+319daccb1+a5edacdfa: no SELF ck_o relabel, every ck_o
# view must carry a native forwarded_clock receipt); (2) all 14 dsfd_dvrlyh views are NATIVE re-exports (12c132d60, main
# exporter, checked vs verdict, ck->ck_o negative_unate) and the CTRL view is native clk->ck_o.
# Same plan / strict bind as DIE9 (plan_mu6 + bind_mu6 die.v 75b71038, STRICT_BIND PASS on branch AND main checker).
# usage: run_mu6n.sh prep  SRC_SHA                  -> source tree + copy DIE9 plan/bind (same host, ep5)
#        run_mu6n.sh chain SRC_SHA CTRL_REF TAG     -> GEN (dv_rvcase, CTRL_REF first) -> GRT -> STA TT/FF/SS -> CLK
set -uo pipefail
D=$(cd "$(dirname "$0")" && pwd)
PH=${1:?phase}; SRC=${2:?src}; CREF=${3:-}; TAG=${4:-mu6n}
export OT_GIT_DIR=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
G=$OT_GIT_DIR
export OT_DIE_REPAIR_CORRIDOR=1
DIEFLOW=804d68ef69adab4aca463317d74bbed100da330d   # corridor die_repeaters (8179ff99b + stop fix; NOT on main), as mu5k
MAIN=c0768b96a8f6c54fa061c73e8cd1e0e982bc9e05      # DIE9 main (last view fallback only; first ref wins)
BASE=results/arch/s81_dv_1016
TBL=$BASE/bind/bind_table_p4l3_mu.json; LP=$BASE/landing/p4l3/land_plan.json
D9=/srv/opentallas-scratch2/claude/s81-die9-mu6
S=$D/steps.log
for r in "$SRC" "$MAIN" "$DIEFLOW" $CREF; do git --git-dir=$G cat-file -e "$r^{commit}" 2>/dev/null || git --git-dir=$G fetch -q origin "$r" || git --git-dir=$G fetch -q origin; done
if [ "$PH" = prep ]; then
  rm -rf "$D/src"; mkdir -p "$D/src"
  git --git-dir=$G archive "$SRC" tools rtl $BASE physical/rom_host_ingest | tar -xf - -C "$D/src" || exit 2
  git --git-dir=$G ls-tree -r --name-only "$SRC" physical | grep -E '(\.v|\.sv|\.vh|/spec\.json)$' | grep -v '^physical/rom_host_ingest' > "$D/phys.lst"
  mapfile -t PF < "$D/phys.lst"; git --git-dir=$G archive "$SRC" -- "${PF[@]}" | tar -xf - -C "$D/src" || exit 2
  echo "SRC $SRC phys_files $(wc -l < "$D/phys.lst")" >> "$S"
  rm -rf "$D/plan_mu6" "$D/bind_mu6"; cp -a "$D9/plan_mu6" "$D9/bind_mu6" "$D/" || exit 2
  grep -h "STRICT_BIND\|DIE_PORT_BIND\|die.v" "$D9/steps.log" | sed 's/^/DIE9_BIND /' >> "$S"
  sha256sum "$D/bind_mu6/bind/die.v" >> "$S"
  sha256sum "$D/bind_mu6/bind/die.v" | grep -q '^75b71038d3ffe04850816771d51899bac6453b49ad79661eb6340c677630a9f2 ' \
    && grep -q "STRICT_BIND PASS" "$D9/steps.log" && echo "STRICT_BIND PASS (DIE9 1b7b9d5d7 bind, die.v 75b71038, identical bind inputs)" >> "$S" || exit 3
  exit 0
fi
if [ "$PH" = chain ]; then
  [ -n "$CREF" ] || exit 2
  grep -q "STRICT_BIND PASS" "$S" || { echo BIND_STRICT_FAIL >> "$S"; exit 3; }
  CT=$(git --git-dir=$G ls-tree -r --name-only "$CREF" physical/ref_tile/ | grep "views/dsfd_ctrl_rg2/forwarded_clock.json")
  [ -n "$CT" ] || { echo "NO_NATIVE_CTRL_VIEW $CREF" >> "$S"; exit 5; }; echo "CTRL_VIEW_FILE $CREF $CT" >> "$S"
  # die tools also read these results files (dv_diecase reach table, cost ledger, MU calendars): add them from SRC
  git --git-dir=$G archive "$SRC" results/arch/die_reach_1016.json results/arch/accepted_cost_ledger_1013.json results/arch/mu_s81_1018 | tar -xf - -C "$D/src" || exit 2
  cd "$D/src" || exit 2
  C=$D/case_$TAG; rm -rf "$C"
  python3 tools/s81_dv/dv_rvcase.py --plan "$D/plan_mu6/plan.json" --bind-dir "$D/bind_mu6/bind" --bind-table "$TBL" --land-plan "$LP" --out "$C" \
    --view-refs "$CREF" "$SRC" "$MAIN" --die-repair --dieflow-ref "$DIEFLOW" --corners tt ff ss --macro-views > "$D/case_gen_$TAG.log" 2>&1
  RC=$?; echo "CASE_RC $TAG $RC corridor=1 macro_views=1 native_consumer=1 ctrl_ref=$CREF src=$SRC" >> "$S"; [ $RC -eq 0 ] || exit $RC
  python3 - "$C" >> "$S" <<'PY'
import json,sys
from pathlib import Path
f=Path(sys.argv[1])/'case.json'; q=json.loads(f.read_text())
cv=q.get('closed_views',{}); print('CTRL_VIEW', cv.get('dsfd_ctrl_rg2','STANDIN'), 'PHY_VIEW', cv.get('ot_hbm3e_phy_v41x_aw30_e8p5_k','STANDIN'))
print('RELAY_VIEWS', sorted({v.split(':')[0][:9] for k,v in cv.items() if k.startswith('dsfd_dvrlyh_')}))
print('STANDINS', q.get('standin_instances'), q.get('label','')[:300])
q['label']='PILOT_NOT_A_GATE '+sys.argv[1].rsplit('/',1)[-1]+': '+q.get('label','')
f.write_text(json.dumps(q,indent=1))
PY
  date > "$C/gen.done"
  CPUS=16 MEMG_GRT=96 MEMG_STA=64 bash "$C/run_all.sh" > "$D/chain_$TAG.log" 2>&1
  echo "CHAIN_RC $TAG $?" >> "$S"
fi
