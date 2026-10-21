#!/bin/bash
# S81-DIE72-G2 (10-21): G1 steps on an immutable snapshot with the G2 inputs --
#   plan_routed_r3 (4 S81-LINKS gap reserves as placement/routing blockages, 748/748 rerouted, station_dirs rebound)
#   + IDX overlay (fff8899d0) + MU72 end-parent overlay (release72/apply_mu72_overlay.py); frame f04198934, LP 21b97190e,
#   views 12c132d60 unchanged.  MAIN = SRC = claude/s81-die72-g2-1021 (main + IDX + MU72 9be8939ec + G2 tools).
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
MAIN=${1:?main}; SRC=${2:?plan_source}; FRAME=f04198934d9a1fdacc81b9501a9ccb5c632ba2ea; LPREF=21b97190eba0b3b306026f23a2408867cd099726
CREF=12c132d60a8f0300056abb216d48ff9588e7f620
G=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
export OT_GIT_DIR=$G OT_DIE_REPAIR_CORRIDOR=1
W=$D/die72-g2; mkdir -p "$W/src"; S=$W/steps.log
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
P=$W/src/results/arch/s81_die72_1021/plan_routed_r3.json
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
python3 tools/s81_dv/dv_rvcase.py --plan "$P" --bind-dir "$W/bind/bind" --bind-table "$T" --land-plan "$LAND" --out "$W/case" --view-refs "$CREF" "$MAIN" "$SRC" --die-repair --dieflow-ref "$MAIN" --dcc-ref "$MAIN" --corners tt ff ss --macro-views --signal-top-layer M8 --gen-safety-diag 'selected72 g2 diagnostic: link gap reserves r3 + MU72 end-parent tops; declared unclosed frame/MU/service parents and source-view scope; no production closure claim' > "$W/case_gen.log" 2>&1
RC=$?; echo "CASE_RC $RC $(date)" >> "$S"
[ $RC -eq 0 ] || exit "$RC"
CPUS=16 MEMG_GRT=96 MEMG_STA=64 bash "$W/case/run_all.sh" > "$W/chain.log" 2>&1
RC=$?; echo "CHAIN_RC $RC $(date)" >> "$S"; exit "$RC"
