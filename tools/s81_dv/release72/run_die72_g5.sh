#!/bin/bash
# S81 DIE72 G5 (S81-LINK5B L5B-G4 10-21): run_die72_g4.sh on plan g5 (dv_floorplan72_g4.py --wb-rows 2 3: W column-B real
#   SerDes lk_WN2/lk_WN3 beside lk_WN0/1, s_0N<->lk_WN2/3 links ~7.9 mm shorter, = pair A length) + RTL L5-RTL e93685328
#   (u_land #(SRAM 1) = CLOSED dsdv_mu_land 263e13fc3) + S81-RTLGAP/head 589110357 (end-slice u_xg -> ot_s81sl_xg_xo).
#   UNBOUND (no CLOSED view yet): s_0N u_lep ot_s81sl_lep_mu_ab (kit s81sl_lepmu, binds in G6), safe8_ntf lanes, u_sl.u_xg
#   xg_xo.  MAIN = SRC = claude/s81-die72-g5-1021.  G1..G4 untouched.  G4 header follows.
# S81 DIE72 G4 (S81-LINK5 L5-G4 10-21): G3 chain + the owner-approved 5th lane pair (10-21 06:00) -- plan G4
#   (results/arch/s81_die72_1021/g4: die 32648 x 25200; W column B link_0_4/0_5 = REAL ot_pdie_serdes lk_WN2/lk_WN3 with
#   links s_0N tx2/tx3 -> lk_WN2/3 tx, lk_WN2/3 rx -> s_0N rx2/rx3; E column B link_1_4/1_5 stay copy-A/B blockage reserves;
#   s_0N = ot_s81sl_slice_lepw_mab_mu_72 2851.2 x 6825.6 (L5-RTL claude/s81-link5-rtl-1021, overlay key dsdv_slice_lepw_mu)),
#   routed HERE on the fleet (dv_route72 + dv_station_dirs72, 0 failures required); land plan = p4l3 + 4 sibling rows
#   (release72/mk_land_plan_g4.py).  Everything else exactly as run_die72_g3.sh.  MAIN = SRC = claude/s81-die72-g5-1021.
#   G1/G2/G3 untouched.
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
MAIN=${1:?main}; SRC=${2:?plan_source}; FRAME=f04198934d9a1fdacc81b9501a9ccb5c632ba2ea; LPREF=21b97190eba0b3b306026f23a2408867cd099726
CREF=12c132d60a8f0300056abb216d48ff9588e7f620
G=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
export OT_GIT_DIR=$G OT_DIE_REPAIR_CORRIDOR=1
W=$D/die72-g5; mkdir -p "$W/src"; S=$W/steps.log
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
python3 tools/s81_dv/dv_route72.py "$R72/g5/plan_unrouted_g5.json" "$W/plan_routed_g5_raw.json" > "$W/route72.log" 2>&1
python3 - "$W/plan_routed_g5_raw.json" <<'PY'
import json,sys
p=json.load(open(sys.argv[1]));f=p['facts']['physical72']
assert not f['routing_failures'],f['routing_failures'][:5]
print('ROUTE72_OK links',len(p['links']),'stations',f['relay_station_count'],'bit_mm',round(p['facts']['bit_mm'],1))
PY
printf 'ROUTE_RC 0 %s\n' "$(date)" >> "$S"
python3 tools/s81_dv/dv_station_dirs72.py "$W/plan_routed_g5_raw.json" "$R72/relay_bodies.json" "$W/plan_routed_g5.json" > "$W/station_dirs.log" 2>&1
printf 'STATION_DIRS_RC 0 %s\n' "$(date)" >> "$S"
P=$W/plan_routed_g5.json
T=$W/bind_table72.json; LAND=$W/land_plan_g5.json
python3 tools/s81_dv/release72/mk_land_plan_g4.py "$BASE/landing/p4l3/land_plan.json" "$LAND" > "$W/land_plan_g5.log" 2>&1
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
python3 tools/s81_dv/dv_rvcase.py --plan "$P" --bind-dir "$W/bind/bind" --bind-table "$T" --land-plan "$LAND" --out "$W/case" --view-refs "$CREF" "$MAIN" "$SRC" --die-repair --dieflow-ref "$MAIN" --dcc-ref "$MAIN" --corners tt ff ss --macro-views --signal-top-layer M8 --gen-safety-diag 'selected72 g5 diagnostic: G5 = G4 + W column-B real SerDes beside lk_WN0/1 + u_land CLOSED dsdv_mu_land SRAM1 + head XB egress u_xg xg_xo (6 real W SerDes, 2 E reserves, s_0N lepw_mab_mu_72 2851.2; svc 3801.6, lepe 2851.2, idx 1209.6, seqhost 475.2x993.6) + MU72 tops on capc5r slice successor; declared unclosed frame/MU/service parents and source-view scope; no production closure claim' > "$W/case_gen.log" 2>&1
RC=$?; echo "CASE_RC $RC $(date)" >> "$S"
[ $RC -eq 0 ] || exit "$RC"
CPUS=16 MEMG_GRT=96 MEMG_STA=64 bash "$W/case/run_all.sh" > "$W/chain.log" 2>&1
RC=$?; echo "CHAIN_RC $RC $(date)" >> "$S"; exit "$RC"
