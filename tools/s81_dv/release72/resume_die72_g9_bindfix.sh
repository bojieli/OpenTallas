#!/bin/bash
# One immutable table-only successor; reuse successful routes, preserve failed bind.
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
OLD=/srv/opentallas-scratch/claude/codex-s81-g9-selected-r2-1021/die72-g9-selected
W=$D/die72-g9-bindfix
FIX=d602169f70800e1108d755f7146ae0ae6c96534d
G=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
export OT_GIT_DIR=$G GIT_DIR=$G OT_DIE_REPAIR_CORRIDOR=1
[ ! -e "$W" ] || { echo 'REFUSE existing immutable successor'; exit 2; }
grep -q '^EXIT_RC 1 ' "$OLD/run.exit"
[ ! -e "$OLD/case" ] || { echo 'REFUSE: predecessor reached GEN'; exit 2; }
mkdir -p "$W"
trap 'rc=$?; printf "EXIT_RC %s %s\n" "$rc" "$(date -Is)" > "$W/run.exit"' EXIT
git --git-dir="$G" cat-file -e "$FIX^{commit}" 2>/dev/null || git --git-dir="$G" fetch -q origin "$FIX"
cp -a --reflink=auto "$OLD/src" "$W/src"
cp "$OLD/snapshot.refs" "$W/snapshot.refs"
printf 'BIND_TABLE_FIX %s\nREUSED_FAILED_UNIT oth-ubuntu-3311561-1792624541\n' "$FIX" >> "$W/snapshot.refs"
for f in plan_routed_g9.json land_plan_g9.json materialized_inputs.sha256; do cp "$OLD/$f" "$W/$f"; done
git --git-dir="$G" show "$FIX:results/arch/s81_die72_1021/g9_assembly/pre_gen/bind_table_g9_corrected.json" > "$W/bind_table_g9.json"
python3 - "$OLD" "$W" <<'PY'
import hashlib,json,sys
from pathlib import Path
old,w=map(Path,sys.argv[1:]);a=json.loads((old/'bind_table_g9.json').read_text());b=json.loads((w/'bind_table_g9.json').read_text())
assert hashlib.sha256((old/'bind_table_g9.json').read_bytes()).hexdigest()=='0dc455e3e7ad658001d6b71a56541ff5ca06d32074631e78e3259608cde765c5'
assert hashlib.sha256((w/'bind_table_g9.json').read_bytes()).hexdigest()=='0feb9b8c74476fbfaf0ce7a99dac3b71290a24c9635e6047d1501e6478a677d7'
c=json.loads(json.dumps(b));c['masters']['dsdv_slice_kv512']['hb_param']='HB';assert c['status_fault_masters'].pop()=='dsdv_slice_kv512';assert c==a
hashes={}
for f in ['plan_routed_g9.json','land_plan_g9.json']:
 h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 assert h(old/f)==h(w/f);hashes[f]=h(w/f)
(w/'reuse_receipt.json').write_text(json.dumps({'scope':'Two table fields only, no rerouting/RTL/helper/clock/cycle change','original_failed_unit':'3311561-1792624541','route_land_hashes':hashes,'reused_plan_links':len(json.loads((w/'plan_routed_g9.json').read_text())['links']),'no_predecessor_GEN':not(old/'case').exists()},indent=2)+'\n')
PY
cd "$W/src"
sha256sum -c "$W/materialized_inputs.sha256" > "$W/source_reuse_check.log"
P=$W/plan_routed_g9.json
T=$W/bind_table_g9.json
LAND=$W/land_plan_g9.json
python3 tools/s81_dv/dv_diecase.py --plan "$P" --out "$W/bind" --bind real --bind-table "$T" --land-plan "$LAND" > "$W/bind.log" 2>&1
printf 'BIND_RC 0 %s\n' "$(date -Is)" >> "$W/steps.log"
python3 tools/s81_dv/dv_rvcase.py --plan "$P" --bind-dir "$W/bind/bind" --bind-table "$T" --land-plan "$LAND" --out "$W/case" --view-refs 12c132d60a8f0300056abb216d48ff9588e7f620 553741303923ab6bab36d67d17f914b1f11896c5 3be5b0ff784590d406f4a1d79c7a7624bac33040 --die-repair --dieflow-ref 1a872af33c8d10d8123f8d4c69198e09cc04fd43 --dcc-ref 1a872af33c8d10d8123f8d4c69198e09cc04fd43 --corners tt ff ss --macro-views --signal-top-layer M8 --gen-safety-diag 'G9 exact available-view diagnostic; table-only KV fixedHB0/fault connection correction; original failed strict bind and routes preserved. CTRL16/QF1/TAP16 actualCLOSED; W6/E4 beneath unhardenedparents, all remaining unqualified masters diagnostic. Syntax/elab only, no runtime/coherence/calendar/wholephysical qualification.' > "$W/case_gen.log" 2>&1
printf 'CASE_RC 0 %s\n' "$(date -Is)" >> "$W/steps.log"
CPUS=16 MEMG_GRT=96 MEMG_STA=64 bash "$W/case/run_all.sh" > "$W/chain.log" 2>&1
printf 'CHAIN_RC 0 %s\n' "$(date -Is)" >> "$W/steps.log"
