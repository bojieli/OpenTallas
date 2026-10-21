#!/bin/bash
# S81 HEAD DIE H2 chain (S81-HEAD / HD-CHAIN 10-21), modelled on release72/run_die72_g7.sh:
#   route (dv_route72 on results/arch/s81_head_1021/h2/plan_unrouted_h2.json, 0 failures + every station hop <= 405 um)
#   -> station dirs (dv_station_dirs72, closed dsfd_dvrlyh_* bodies; 682 SN -> NS substitution as G7)
#   -> land plan (head72/hd_land_plan.py: one MODEL row per stationed lane, bundle-age K, 276l long tiles; FAILS rather
#      than emit a K 1 placeholder) -> bind table (head72/hd_bind.py: G7 base die-infrastructure keys + head masters from
#      results/arch/s81_head_1021/ports.json, rank-0 row0/ten straps, instance orientations)
#   -> dv_diecase --bind real (STRICT die_port_bind) -> dv_rvcase (tt ff ss, macro views, die repair, M8)
#   -> case/run_all.sh (GEN -> GRT -> STA -> CLK).
# Die 15876 x 22636.8 um (359.4 mm2), 311 blocks / 437 links: 253 ot_s81hd_tile, 13 spo + 13 spr, ctl, lep, 13 lanes, 17 SerDes.
# Widths = ports.json (HD-CTL b4f571642): bus B 565 (682 lanes where a station / crossing), ctl <-> lane 3 x 276 each way,
# ctl <-> lep 5 x 276 each way, lep <-> lk_WN* 2 x 276, lane <-> SerDes 512 / 562 (abutted, 0 stations).
# UNBOUND (no CLOSED view exists; source-view stand-ins in the case): ot_s81hd_tile / spo / spr (kits s81hd_*_m/_f gates),
#   ot_s81hd_ctl / lep / lane (kits owed), ot_pdie_serdes_col (G7 stand-in).  CLOSED: dsfd_dvrlyh_* relays, dsfd_dvland_*
#   landings, dsfd_rly_1_WN reset stations.
# H2: ctl glue and CLOSED M7 sequencer are peers in clctl; 108um face gap, <=334.8um conservative face reach, zero added cycles.
# Usage: run_head_h2.sh MAIN [SRC]   (MAIN = SRC = claude/s81-head-h2-1021 commit)
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
MAIN=${1:?main}; SRC=${2:-$1}
CREF=12c132d60a8f0300056abb216d48ff9588e7f620
G=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
export OT_GIT_DIR=$G OT_DIE_REPAIR_CORRIDOR=1
W=${HD_RUN_DIR:-$D/head-h2}; mkdir -p "$W/src"; S=$W/steps.log
for r in "$MAIN" "$SRC" "$CREF"; do git --git-dir="$G" cat-file -e "$r^{commit}" 2>/dev/null || git --git-dir="$G" fetch -q origin "$r"; done
BASE=results/arch/s81_dv_1016
printf 'MAIN %s\nPLAN %s\nVIEWS %s\n' "$MAIN" "$SRC" "$CREF" > "$W/snapshot.refs"
git --git-dir="$G" archive "$MAIN" tools rtl "$BASE" physical/rom_host_ingest results/arch/die_reach_1016.json results/arch/accepted_cost_ledger_1013.json results/arch/mu_s81_1018 | tar -xf - -C "$W/src"
git --git-dir="$G" ls-tree -r --name-only "$MAIN" physical | grep -E '(\.v|\.sv|\.vh|/spec\.json)$' | grep -v '^physical/rom_host_ingest' > "$W/phys.lst"
mapfile -t PF < "$W/phys.lst"; git --git-dir="$G" archive "$MAIN" -- "${PF[@]}" | tar -xf - -C "$W/src"
git --git-dir="$G" archive "$SRC" results/arch/s81_head_1021 results/arch/s81_die72_1021/relay_bodies.json tools/s81_dv/head72 | tar -xf - -C "$W/src"
cd "$W/src"
grep -q 'from frame_bind import' tools/s81_dv/dv_bind.py
grep -q "station_dirs" tools/s81_dv/dv_diecase.py
export GIT_DIR=$G
R=results/arch/s81_head_1021/h2
python3 tools/s81_dv/dv_route72.py "$R/plan_unrouted_h2.json" "$W/plan_routed_h2_raw.json" > "$W/route72.log" 2>&1
python3 tools/s81_dv/head72/hd_plan.py check "$W/plan_routed_h2_raw.json" > "$W/route_check.json"
printf 'ROUTE_RC 0 %s\n' "$(date)" >> "$S"
python3 tools/s81_dv/dv_station_dirs72.py "$W/plan_routed_h2_raw.json" results/arch/s81_die72_1021/relay_bodies.json "$W/plan_routed_h2.json" > "$W/station_dirs.log" 2>&1
printf 'STATION_DIRS_RC 0 %s\n' "$(date)" >> "$S"
P=$W/plan_routed_h2.json
T=$W/bind_table_h2.json; LAND=$W/land_plan_h2.json
python3 tools/s81_dv/head72/hd_land_plan.py "$P" "$LAND" > "$W/land_plan.log" 2>&1
printf 'LAND_PLAN_RC 0 %s\n' "$(date)" >> "$S"
python3 tools/s81_dv/head72/hd_bind.py --plan "$P" --base "$BASE/bind/bind_table_p4l3_mu.json" --ports results/arch/s81_head_1021/ports.json --land-plan "$LAND" --out "$T" > "$W/bind_table.log" 2>&1
printf 'BIND_TABLE_RC 0 %s\n' "$(date)" >> "$S"
set +e
python3 tools/s81_dv/dv_diecase.py --plan "$P" --out "$W/bind" --bind real --bind-table "$T" --land-plan "$LAND" > "$W/bind.log" 2>&1
RC=$?; echo "BIND_RC $RC $(date)" >> "$S"
[ $RC -eq 0 ] || exit "$RC"
python3 tools/s81_dv/dv_rvcase.py --plan "$P" --bind-dir "$W/bind/bind" --bind-table "$T" --land-plan "$LAND" --out "$W/case" --view-refs "$CREF" "$MAIN" "$SRC" --die-repair --dieflow-ref "$MAIN" --dcc-ref "$MAIN" --corners tt ff ss --macro-views --signal-top-layer M8 --gen-safety-diag 'S81 head die H2 diagnostic (HD-CHAIN 10-21): 359.4 mm2, 253 head-bundle tiles + 13/13 spine nodes + ctl/lep/13 lanes + 17 SerDes; head tile/spo/spr/glue/lep/lane masters and ot_pdie_serdes_col is an UNCLOSED source-view stand-in (no CLOSED view exists yet); the exact M7 dsfd_mtp_seq peer plus relays, landings and reset stations bind CLOSED views; land plan = MODEL rows (F = ceil(0.47 N)), die STA re-derives; rank-0 straps; no production closure claim' > "$W/case_gen.log" 2>&1
RC=$?; echo "CASE_RC $RC $(date)" >> "$S"
[ $RC -eq 0 ] || exit "$RC"
CPUS=16 MEMG_GRT=96 MEMG_STA=64 bash "$W/case/run_all.sh" > "$W/chain.log" 2>&1
RC=$?; echo "CHAIN_RC $RC $(date)" >> "$S"; exit "$RC"
