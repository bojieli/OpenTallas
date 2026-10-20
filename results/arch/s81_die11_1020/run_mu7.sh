#!/bin/bash
# S81-DIE11 10-20: mu7 die chain (122 frames, owner/LEAD9: no frame drops). Plan = mu6 (p4l MU, idxrd 0, n32s CTRL body
# 388.8x324 centred per pair, array +86.4) + --rsv-vcol K (K x 43.2-um V lattice columns in every svc_rs column gap).
# Strict bind (branch checker + origin/main die_port_bind) -> real-view case (native views 12c132d60) with
# --signal-top-layer M8 (signals M2-M8, clock M5-M9; set_wire_rc -layer M8 in place+STA; repeater RC M8) -> chain
# (repeaters corridor + fclk payload equalizer -> GRT -> STA TT/FF/SS -> die clock check, 67ec checker on main).
# usage: run_mu7.sh SRC_SHA K TAG
set -uo pipefail
D=$(cd "$(dirname "$0")" && pwd)
SRC=${1:?src}; K=${2:?vcol}; TAG=${3:?tag}
export OT_GIT_DIR=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
G=$OT_GIT_DIR
export OT_DIE_REPAIR_CORRIDOR=1
CREF=12c132d60a8f0300056abb216d48ff9588e7f620     # native 14 dsfd_dvrlyh views + n32s CTRL native view (DIE10, as the M8 pilot)
VMAIN=c0768b96a8f6c54fa061c73e8cd1e0e982bc9e05    # last view fallback (as mu6n / the M8 pilot)
MAIN=98070b1b5b27ac879d0daab47827842412f56684                                     # origin/main 10-20 13:4x: 66736dcff M8 merge + 67ec ring-aware clock checker
BASE=results/arch/s81_dv_1016
TBL=$BASE/bind/bind_table_p4l3_mu.json; LP=$BASE/landing/p4l3/land_plan.json
W=$D/$TAG; mkdir -p "$W"; S=$W/steps.log
for r in "$SRC" "$CREF" "$VMAIN" "$MAIN"; do git --git-dir=$G cat-file -e "$r^{commit}" 2>/dev/null || git --git-dir=$G fetch -q origin "$r" 2>/dev/null || git --git-dir=$G fetch -q origin; done
MAIN=$(git --git-dir=$G rev-parse "$MAIN^{commit}") || exit 2
rm -rf "$W/src"; mkdir -p "$W/src"
git --git-dir=$G archive "$SRC" tools rtl $BASE physical/rom_host_ingest results/arch/die_reach_1016.json results/arch/accepted_cost_ledger_1013.json results/arch/mu_s81_1018 | tar -xf - -C "$W/src" || exit 2
git --git-dir=$G ls-tree -r --name-only "$SRC" physical | grep -E '(\.v|\.sv|\.vh|/spec\.json)$' | grep -v '^physical/rom_host_ingest' > "$W/phys.lst"
mapfile -t PF < "$W/phys.lst"; git --git-dir=$G archive "$SRC" -- "${PF[@]}" | tar -xf - -C "$W/src" || exit 2
echo "SRC $SRC K $K phys_files $(wc -l < "$W/phys.lst") $(date)" >> "$S"
cd "$W/src" || exit 2
for r in $(python3 -c "import json;t=json.load(open('$TBL'));print(' '.join(sorted({v.get('commit') or v['ref'] for v in t.get('land_views',{}).values()})))"); do
  git --git-dir=$G cat-file -e "$r^{commit}" 2>/dev/null || git --git-dir=$G fetch -q origin "$r" || echo "FETCH_FAIL $r" >> "$S"
done
args=(--layout p4 --tier-w 276 --lanes 4 --p4l --p4h-drop 6 --frame-w 1436.832 --mu 1 --pathfix --lk-slots $BASE/p4l_lkcol/plan.json --ctrl-view-size 388.8 324 --array-y-shift 86.4)
python3 tools/s81_dv/dv_plan.py "${args[@]}" --revision dv-p4l-mu1-mu6 --out "$W/plan_mu6chk" > "$W/plan_mu6chk.log" 2>&1
python3 tools/s81_dv/dv_plan.py "${args[@]}" --rsv-vcol "$K" --revision dv-p4l-mu1-$TAG --out "$W/plan" > "$W/plan.log" 2>&1
RC=$?; echo "PLAN_RC $RC" >> "$S"; [ $RC -eq 0 ] || exit $RC
python3 - "$W/plan/plan.json" >> "$S" <<'PY'
import json,sys
f=json.load(open(sys.argv[1]))['facts']
print('PLAN_FACTS n_frames', f.get('n_frames'), 'rom_slots', f.get('rom_slots'), 'die_um', f.get('die_um'), 'worst_cut', f.get('worst_cut'),
      'cut_over', f.get('cut_windows_over_limit'), 'over_reach', f.get('over_reach_bits'), 'relays', f.get('relays'), 'bit_mm', f.get('bit_mm'))
assert f.get('n_frames') == 122 and f.get('rom_slots') == 1130, 'mu7 must preserve all 122 frames / 1130 ROM slots (LEAD9 10-20)'
PY
[ $? -eq 0 ] || { echo FRAME_GUARD_FAIL >> "$S"; exit 6; }
python3 tools/s81_dv/dv_diecase.py --plan "$W/plan/plan.json" --out "$W/bind" --bind real --bind-table "$TBL" --land-plan "$LP" > "$W/bind.log" 2>&1
echo "BIND_RC $?" >> "$S"; grep -h DIE_PORT_BIND "$W/bind/bind/port_bind.log" | tail -1 >> "$S"
rm -rf "$W/srcm"; cp -a "$W/src" "$W/srcm"; git --git-dir=$G show "$MAIN:tools/die_port_bind.py" > "$W/srcm/tools/die_port_bind.py"
(cd "$W/srcm" && python3 tools/s81_dv/dv_diecase.py --plan "$W/plan/plan.json" --out "$W/bind_mainchk" --bind real --bind-table "$TBL" --land-plan "$LP" > "$W/bind_mainchk.log" 2>&1; echo "MAINCHK_RC $?" >> "$S")
grep -h DIE_PORT_BIND "$W/bind_mainchk/bind/port_bind.log" | tail -1 >> "$S"
sha256sum "$W/bind/bind/die.v" "$W/bind_mainchk/bind/die.v" >> "$S"
python3 - "$W" >> "$S" <<'PY'
import json,sys
from pathlib import Path
ok=True
for b in ('bind','bind_mainchk'):
    p=Path(sys.argv[1])/b/'bind/port_bind.json'
    if not p.exists(): print(b,'NO_PORT_REPORT'); ok=False; continue
    x=json.loads(p.read_text()); s=x.get('summary',{})
    print(b, x.get('verdict'), 'undriven', s.get('undriven_net_bits'), 'tied', s.get('input_tied'), 'unconn', s.get('input_unconnected'), 'stub', s.get('stub_masters'), 'unbound', s.get('unbound_masters'))
    lg=(Path(sys.argv[1])/b/'bind/port_bind.log'); lp=[l for l in (lg.read_text().splitlines() if lg.exists() else []) if l.startswith('DIE_PORT_BIND ')]
    ok = ok and x.get('verdict')=='PASS' and bool(lp) and lp[-1].startswith('DIE_PORT_BIND PASS')
print('STRICT_BIND', 'PASS' if ok else 'FAIL')
PY
grep -q "STRICT_BIND PASS" "$S" || exit 4
C=$W/case
python3 tools/s81_dv/dv_rvcase.py --plan "$W/plan/plan.json" --bind-dir "$W/bind/bind" --bind-table "$TBL" --land-plan "$LP" --out "$C" \
  --view-refs "$CREF" "$SRC" "$VMAIN" --die-repair --dieflow-ref "$SRC" --dcc-ref "$MAIN" --corners tt ff ss --macro-views \
  --signal-top-layer M8 > "$W/case_gen.log" 2>&1
RC=$?; echo "CASE_RC $RC M8 corridor=1 macro_views=1 ctrl_ref=$CREF dieflow=$SRC dcc=$MAIN" >> "$S"; [ $RC -eq 0 ] || exit $RC
grep -c "set_wire_rc -signal -layer M8" "$C/run.tcl" "$C"/sta_*.tcl >> "$S"; grep -o "rc_layer {M[0-9]}" "$C/die_repeaters_step.tcl" | sort -u >> "$S"
grep -o "signal M2-M[0-9] -clock M5-M9" "$C/run.tcl" >> "$S"
python3 - "$C" "$TAG" >> "$S" <<'PY'
import json,sys
from pathlib import Path
f=Path(sys.argv[1])/'case.json'; q=json.loads(f.read_text())
cv=q.get('closed_views',{}); print('CTRL_VIEW', cv.get('dsfd_ctrl_rg2','STANDIN'), 'PHY_VIEW', cv.get('ot_hbm3e_phy_v41x_aw30_e8p5_k','STANDIN'))
print('RELAY_VIEWS', sorted({v.split(':')[0][:9] for k,v in cv.items() if k.startswith('dsfd_dvrlyh_')}))
print('STANDINS', q.get('standin_instances'))
q['label']='PILOT_NOT_A_GATE mu7 '+sys.argv[2]+' (122 frames, M8 signals): '+q.get('label','')
f.write_text(json.dumps(q,indent=1))
PY
date > "$C/gen.done"
CPUS=16 MEMG_GRT=96 MEMG_STA=64 bash "$C/run_all.sh" > "$W/chain.log" 2>&1
echo "CHAIN_RC $TAG $? $(date)" >> "$S"
