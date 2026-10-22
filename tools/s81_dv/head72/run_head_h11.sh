#!/bin/bash
# H11 (STW-S81c-DIE 10-22): HD_VARIANT=h11m (MAIN: glue R3m 2160x3888, ch_ctl 864) | h11f (FB: glue R3f 2592x4320, ch_ctl 756).
#   Successor of H10b (h10bm GRT 30/30 not overflow 0: all 1,215 violation gcells at the ctl E face, x 10.5-11 mm,
#   y 10-13 mm = the ctl band; STA relay_reset hold TT -16.9 ns = forwarded-clock capture class). H11 = H10b binding
#   (closed spr + spo) with a taller ctl band (more H tracks beside the E face) and the cap21-23 case flags
#   (co-forwarded relay reset + post-GRT hold ECO, regional die clocks, reset-chain placement/repair).
# Original H10 notes follow.
# H10 (STW-S81-HEAD 10-21): HD_VARIANT=h10m (MAIN, ctl 2160x3888) | h10f (FALLBACK, ctl 2592x4320); plans by hd_h10_plan.py
# S81 HEAD DIE H10 chain (S81-HEAD / HD-CHAIN 10-21), modelled on release72/run_die72_g7.sh:
#   route (dv_route72 on results/arch/s81_head_1021/h10/plan_unrouted_h10.json, 0 failures + every station hop <= 405 um)
#   -> station dirs (dv_station_dirs72, closed dsfd_dvrlyh_* bodies; 682 SN -> NS substitution as G7)
#   -> land plan (head72/hd_land_plan.py: one MODEL row per stationed lane, bundle-age K, 276l long tiles; FAILS rather
#      than emit a K 1 placeholder) -> bind table (head72/hd_bind.py: G7 base die-infrastructure keys + head masters from
#      results/arch/s81_head_1021/ports.json, rank-0 row0/ten straps, instance orientations)
#   -> dv_diecase --bind real (STRICT die_port_bind) -> dv_rvcase (tt ff ss, macro views, die repair, M8)
#   -> case/run_all.sh (GEN -> GRT -> STA -> CLK).
# Die 15876 x 22636.8 um (424 (h10m) / 450 (h10f) mm2, ctl glue enlarged to <=3.83 pins/um, lane-regional SerDes (STW-S81-HEAD H10)), 311 blocks / 437 links: 253 ot_s81hd_tile, 13 spo + 13 spr, ctl, lep, 13 lanes, 17 SerDes.
# Widths = ports.json (HD-CTL b4f571642): bus B 565 (682 lanes where a station / crossing), ctl <-> lane 3 x 276 each way,
# ctl <-> lep 5 x 276 each way, lep <-> lk_WN* 2 x 276, lane <-> SerDes 512 / 562 (abutted, 0 stations).
# UNBOUND (no CLOSED view exists; source-view stand-ins in the case): ot_s81hd_tile / spo / spr (kits s81hd_*_m/_f gates),
#   ot_s81hd_ctl / lep / lane (kits owed), ot_pdie_serdes_col (G7 stand-in).  CLOSED: dsfd_dvrlyh_* relays, dsfd_dvland_*
#   landings, dsfd_rly_1_WN reset stations.
# H10: ctl glue and CLOSED M7 sequencer are peers in clctl; 108um face gap, <=334.8um conservative face reach, zero added cycles.
# Usage: run_head_h10.sh MAIN [SRC]   (MAIN = SRC = claude/s81-head-h10-1021 commit)
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
MAIN=${1:?main}; SRC=${2:-$1}
CREF=12c132d60a8f0300056abb216d48ff9588e7f620
G=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
export OT_GIT_DIR=$G OT_DIE_REPAIR_CORRIDOR=1
W=${HD_RUN_DIR:-$D/head-h10}; mkdir -p "$W/src"; S=$W/steps.log
for r in "$MAIN" "$SRC" "$CREF" ${GLUE_RECORD:-} ${GLUE_SOURCE:-} ${GLUE_LINKS_REF:-}; do git --git-dir="$G" cat-file -e "$r^{commit}" 2>/dev/null || git --git-dir="$G" fetch -q origin "$r"; done
BASE=results/arch/s81_dv_1016
printf 'MAIN %s\nPLAN %s\nVIEWS %s\n' "$MAIN" "$SRC" "$CREF" > "$W/snapshot.refs"
[ -n "${GLUE_KIT:-}" ] && printf 'GLUE %s RECORD %s SOURCE %s\n' "$GLUE_KIT" "$GLUE_RECORD" "$GLUE_SOURCE" >> "$W/snapshot.refs"
git --git-dir="$G" archive "$MAIN" tools rtl "$BASE" physical/rom_host_ingest results/arch/die_reach_1016.json results/arch/accepted_cost_ledger_1013.json results/arch/mu_s81_1018 | tar -xf - -C "$W/src"
git --git-dir="$G" ls-tree -r --name-only "$MAIN" physical | grep -E '(\.v|\.sv|\.vh|/spec\.json)$' | grep -v '^physical/rom_host_ingest' > "$W/phys.lst"
mapfile -t PF < "$W/phys.lst"; git --git-dir="$G" archive "$MAIN" -- "${PF[@]}" | tar -xf - -C "$W/src"
git --git-dir="$G" archive "$SRC" results/arch/s81_head_1021 results/arch/s81_die72_1021/relay_bodies.json tools/s81_dv/head72 | tar -xf - -C "$W/src"
cd "$W/src"
grep -q 'from frame_bind import' tools/s81_dv/dv_bind.py
grep -q "station_dirs" tools/s81_dv/dv_diecase.py
export GIT_DIR=$G
R=results/arch/s81_head_1021/${HD_VARIANT:?HD_VARIANT h11m|h11f}
PU=$R/plan_unrouted_h10.json
# H11 r4 (STW-S81c-DIE2-C25 10-22): GLUE_KIT=s81hd_glue_r5m|r5f|r6m|r6f GLUE_RECORD=<record commit holding its CLOSED view>
#   GLUE_SOURCE=<kit source commit> [GLUE_LINKS_REF] binds the first CLOSED ctl glue view (R6: ctl endpoints at its new faces)
if [ -n "${GLUE_KIT:-}" ]; then
  python3 tools/s81_dv/head72/hd_glue_bind_plan.py "$PU" "$W/plan_unrouted_glue.json" --kit "$GLUE_KIT" --record "${GLUE_RECORD:?}" \
    --source "${GLUE_SOURCE:?}" ${GLUE_LINKS_REF:+--links-ref "$GLUE_LINKS_REF"} > "$W/glue_plan.log" 2>&1
  PU=$W/plan_unrouted_glue.json; printf 'GLUE_PLAN_RC 0 %s %s\n' "$GLUE_KIT" "$(date)" >> "$S"
fi
python3 tools/s81_dv/dv_route72.py "$PU" "$W/plan_routed_h10_raw.json" > "$W/route72.log" 2>&1
python3 tools/s81_dv/head72/hd_plan.py check "$W/plan_routed_h10_raw.json" > "$W/route_check.json"
printf 'ROUTE_RC 0 %s\n' "$(date)" >> "$S"
python3 tools/s81_dv/dv_station_dirs72.py "$W/plan_routed_h10_raw.json" results/arch/s81_die72_1021/relay_bodies.json "$W/plan_routed_h10.json" > "$W/station_dirs.log" 2>&1
printf 'STATION_DIRS_RC 0 %s\n' "$(date)" >> "$S"
P=$W/plan_routed_h10.json
T=$W/bind_table_h10.json; LAND=$W/land_plan_h10.json
python3 tools/s81_dv/head72/hd_land_plan.py "$P" "$LAND" > "$W/land_plan.log" 2>&1
printf 'LAND_PLAN_RC 0 %s\n' "$(date)" >> "$S"
python3 tools/s81_dv/head72/hd_bind.py --plan "$P" --base "$BASE/bind/bind_table_p4l3_mu.json" --ports results/arch/s81_head_1021/ports.json --land-plan "$LAND" --out "$T" > "$W/bind_table.log" 2>&1
printf 'BIND_TABLE_RC 0 %s\n' "$(date)" >> "$S"
# H11 r3 (STW-S81c-DIE2): LOGICAL cluster roots exceed the geometric extent+reach gate (45 roots); allowed by owner rule
# 10-17 (b) (cluster roots may exceed if child-flop spread <=80 ps TT+FF and links landed: gen_safety 154/154 landed),
# judged by the measured dieclk check -> H11_REGIONS_DIAG labels the case a clock-region diagnostic.
# H11 r2: the merged 72-frame dv_bind defaults to GEOMETRIC clock regions (ck_g<i>_<j>), which cut the spine <-> first-tile
# chain links of the head (H11 r1 gen_safety C1 69/196 unlanded). The head keeps its H10 LOGICAL (group) regions.
python3 - "$T" "${H11_REGIONS:-logical}" <<'PY'
import json, sys
p, mode = sys.argv[1:]; t = json.load(open(p)); t.setdefault('clock_regions', {})['mode'] = mode; json.dump(t, open(p, 'w'), indent=1)
print('H11_CLOCK_REGIONS', mode)
PY
set +e
python3 tools/s81_dv/dv_diecase.py --plan "$P" --out "$W/bind" --bind real --bind-table "$T" --land-plan "$LAND" > "$W/bind.log" 2>&1
RC=$?; echo "BIND_RC $RC $(date)" >> "$S"
[ $RC -eq 0 ] || exit "$RC"
python3 tools/s81_dv/dv_rvcase.py --plan "$P" --bind-dir "$W/bind/bind" --bind-table "$T" --land-plan "$LAND" --out "$W/case" --view-refs "$CREF" "$MAIN" "$SRC" ${GLUE_RECORD:+"$GLUE_RECORD"} --die-repair --dieflow-ref 33432c494a461c70406ffe5623fabae9548f6293 --dcc-ref "$MAIN" --corners tt ff ss --macro-views --signal-top-layer M8 --rfw --hold-eco --dieclk --fck-out-pin --rs-chain-place --rs-repair --dieclk-split-um 2000 ${H11_REGIONS_DIAG:+--clock-region-diag "$H11_REGIONS_DIAG"} --gen-safety-diag 'S81 head die H11 (STW-S81c-DIE): H10b + taller ctl band + cap21-23 case flags; H10 notes: (HD-CHAIN 10-21): 424 (h10m) / 450 (h10f) mm2, ctl glue enlarged to <=3.83 pins/um, lane-regional SerDes (STW-S81-HEAD H10), 253 head-bundle tiles + 13/13 spine nodes + ctl/lep/13 lanes + 17 SerDes; head tile/spo/glue/regional-lep/lane masters and ot_pdie_serdes_col is an UNCLOSED source-view stand-in (no CLOSED view exists yet); all13 exact CLOSED SPR m4 R0 bodies in existing reserves plus exact M7 dsfd_mtp_seq peer and relays, landings and reset stations bind CLOSED views; land plan = MODEL rows (F = ceil(0.47 N)), die STA re-derives; rank-0 straps; three explicit endpoint roots C/A/B and corresponding reset forests; regional child packing/reach and physical closure are owed; no production closure claim' > "$W/case_gen.log" 2>&1
RC=$?; echo "CASE_RC $RC $(date)" >> "$S"
[ $RC -eq 0 ] || exit "$RC"
[ "${H11_GEN_ONLY:-0}" = 1 ] && exit 0
CPUS=16 MEMG_GRT=96 MEMG_STA=64 bash "$W/case/run_all.sh" > "$W/chain.log" 2>&1
RC=$?; echo "CHAIN_RC $RC $(date)" >> "$S"; exit "$RC"
