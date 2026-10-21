#!/bin/bash
# S81 DIE72 G3 (LEAD-S81-G3 10-21): G2 chain with the slot fixes -- plan G3 (results/arch/s81_die72_1021/g3:
#   die 32302.4 x 25200, real 518.4 x 3844.8 SerDes slots + 2 reserves/side as blockages, svc 1728 x 3801.6 x16, ctrl row +43.2,
#   lepe MU72 parents 2851.2 wide, idx readers 1036.8 x 1209.6, seqhost 475.2 x 993.6) routed HERE on the fleet (dv_route72 +
#   dv_station_dirs72, 0 failures required), MU72 tops with u_sl = ot_s81sl_slice_c1x_k8_cap5r_lp (capc5r + CAP reset forests),
#   IDX overlay + MU72 overlay as G2; frame f04198934, LP 21b97190e, views 12c132d60 + MAIN (every CLOSED view on main).
#   MAIN = SRC = claude/s81-die72-g3-1021.  G1 (ep7) and G2 (ep6) untouched.
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
MAIN=${1:?main}; SRC=${2:?plan_source}; FRAME=f04198934d9a1fdacc81b9501a9ccb5c632ba2ea; LPREF=21b97190eba0b3b306026f23a2408867cd099726
CREF=12c132d60a8f0300056abb216d48ff9588e7f620
G=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
export OT_GIT_DIR=$G OT_DIE_REPAIR_CORRIDOR=1
W=$D/die72-g3; mkdir -p "$W/src"; S=$W/steps.log
for r in "$MAIN" "$SRC" "$FRAME" "$LPREF" "$CREF"; do git --git-dir="$G" cat-file -e "$r^{commit}" 2>/dev/null || git --git-dir="$G" fetch -q origin "$r"; done
BASE=results/arch/s81_dv_1016
printf 'MAIN %s\nPLAN %s\nFRAME %s\nLP %s\nVIEWS %s\n' "$MAIN" "$SRC" "$FRAME" "$LPREF" "$CREF" > "$W/snapshot.refs"
git --git-dir="$G" archive "$MAIN" tools rtl "$BASE" physical/rom_host_ingest results/arch/die_reach_1016.json results/arch/accepted_cost_ledger_1013.json results/arch/mu_s81_1018 | tar -xf - -C "$W/src"
git --git-dir="$G" ls-tree -r --name-only "$MAIN" physical | grep -E '(\.v|\.sv|\.vh|/spec\.json)$' | grep -v '^physical/rom_host_ingest' > "$W/phys.lst"
mapfile -t PF < "$W/phys.lst"; git --git-dir="$G" archive "$MAIN" -- "${PF[@]}" | tar -xf - -C "$W/src"
git --git-dir="$G" archive "$SRC" results/arch/s81_die72_1021 tools/s81_dv/release72 physical/ref_tile/s81_mu72_assembly | tar -xf - -C "$W/src"
git --git-dir="$G" show "$FRAME:tools/s81_dv/frame_bind.py" > "$W/src/tools/s81_dv/frame_bind.py"
cd "$W/src"
if ! grep -q 'from frame_bind import' tools/s81_dv/dv_bind.py; then patch --batch -p1 < tools/s81_dv/release72/frame_bind.patch; fi
grep -q "station_dirs" tools/s81_dv/dv_diecase.py
export GIT_DIR=$G
R72=results/arch/s81_die72_1021
python3 tools/s81_dv/dv_route72.py "$R72/g3/plan_unrouted_g3.json" "$W/plan_routed_g3_raw.json" > "$W/route72.log" 2>&1
python3 - "$W/plan_routed_g3_raw.json" <<'PY'
import json,sys
p=json.load(open(sys.argv[1]));f=p['facts']['physical72']
assert not f['routing_failures'],f['routing_failures'][:5]
print('ROUTE72_OK links',len(p['links']),'stations',f['relay_station_count'],'bit_mm',round(p['facts']['bit_mm'],1))
PY
printf 'ROUTE_RC 0 %s\n' "$(date)" >> "$S"
python3 tools/s81_dv/dv_station_dirs72.py "$W/plan_routed_g3_raw.json" "$R72/relay_bodies.json" "$W/plan_routed_g3.json" > "$W/station_dirs.log" 2>&1
printf 'STATION_DIRS_RC 0 %s\n' "$(date)" >> "$S"
P=$W/plan_routed_g3.json
T=$W/bind_table72.json; LAND=$BASE/landing/p4l3/land_plan.json
python3 tools/s81_dv/frame_bind.py --plan "$P" --table "$BASE/bind/bind_table_p4l3_mu.json" --out "$T" --source-ref "$LPREF" > "$W/frame_table.log" 2>&1
printf 'FRAME_TABLE_RC 0 %s\n' "$(date)" >> "$S"
python3 tools/s81_dv/recovery_idx4_1021/apply_overlay.py "$T"
printf 'IDX_OVERLAY_RC 0 %s\n' "$(date)" >> "$S"
python3 tools/s81_dv/release72/apply_mu72_overlay.py "$T" > "$W/mu72_overlay.log" 2>&1
printf 'MU72_OVERLAY_RC 0 %s\n' "$(date)" >> "$S"
set +e
python3 tools/s81_dv/dv_diecase.py --plan "$P" --out "$W/bind" --bind real --bind-table "$T" --land-plan "$LAND" > "$W/bind.log" 2>&1
RC=$?; echo "BIND_RC $RC $(date)" >> "$S"
[ $RC -eq 0 ] || exit "$RC"
python3 tools/s81_dv/dv_rvcase.py --plan "$P" --bind-dir "$W/bind/bind" --bind-table "$T" --land-plan "$LAND" --out "$W/case" --view-refs "$CREF" "$MAIN" "$SRC" --die-repair --dieflow-ref "$MAIN" --dcc-ref "$MAIN" --corners tt ff ss --macro-views --signal-top-layer M8 --gen-safety-diag 'selected72 g3 diagnostic: G3 slots (real SerDes + 2 reserves/side, svc 3801.6, lepe 2851.2, idx 1209.6, seqhost 475.2x993.6) + MU72 tops on capc5r slice successor; declared unclosed frame/MU/service parents and source-view scope; no production closure claim' > "$W/case_gen.log" 2>&1
RC=$?; echo "CASE_RC $RC $(date)" >> "$S"
[ $RC -eq 0 ] || exit "$RC"
CPUS=16 MEMG_GRT=96 MEMG_STA=64 bash "$W/case/run_all.sh" > "$W/chain.log" 2>&1
RC=$?; echo "CHAIN_RC $RC $(date)" >> "$S"; exit "$RC"
