#!/usr/bin/env bash
# S81 landed bottom-up FALLBACK launcher -- FALLBACK-PLAN-PREP-2, 2026-10-27. UNEXECUTED.
# Plan: results/fallback_plans/s81/README.md. PLANS ONLY until the OWNER trigger fires at 2026-10-29 12:00 PDT.
#
#   FALLBACK_TRIGGER=FIRED ./launch_fallback.sh <COORD-RULING-ID> [stage...]      # DRY_RUN=1 (default): print only
#   FALLBACK_TRIGGER=FIRED DRY_RUN=0 ./launch_fallback.sh <COORD-RULING-ID> A B    # really submit stages A and B
#
# Stages (dependency order): A plan event -> B region clock + die GRT -> C strict bind -> D kits -> E die STA.
# Every heavy step goes through the ot-run head on intel2 with an honest --mem (measured where known). Never epyc1.
# <=400k cells per OpenROAD run. Scratch only. Fill in the TODO(T0) items from the COORD ruling before DRY_RUN=0.
set -euo pipefail

TRIGGER_EPOCH=1793300400            # date -d "2026-10-29 12:00 -0700" +%s
DRY_RUN="${DRY_RUN:-1}"
RULING="${1:-}"
shift || true
STAGES="${*:-A B C D E}"

die() { echo "launch_fallback(s81): $*" >&2; exit 2; }
[ "${FALLBACK_TRIGGER:-}" = "FIRED" ] || die "refused: FALLBACK_TRIGGER != FIRED (owner trigger 2026-10-29 12:00 PDT)"
[ "$(date +%s)" -ge "$TRIGGER_EPOCH" ] || die "refused: before 2026-10-29 12:00 PDT"
[ -n "$RULING" ] || die "refused: give the COORD ruling id (COORD-REVIEW-QUEUE line) that starts the S81 fallback"

OTRUN=(ssh -o ControlPath=none intel2 ~/.local/bin/ot-run)
SRC_SHA="${SRC_SHA:?TODO(T0): main sha after ROOT-MERGE of thin-bank/PHY-merge/hop-guard/region-trunk tools}"
RUN="${RUN:-/srv/opentallas-scratch2/claude/fallback-s81-run-1029}"     # created on intel1+intel2 scratch2
SRC="$RUN/src"                                                            # pinned worktree at SRC_SHA (sparse ok)
TD="$SRC/tools/die_plan"
PLAN_IN="${PLAN_IN:-/srv/opentallas-scratch2/claude/codex-s81-pd14-0818/fallback_g2_svc13/die_plan.json}"
PLAN_SHA="${PLAN_SHA:-b80fac422de54cb4da53f66e3d4be54a69ad2f62b4d0d71e97735daa145b7d5d}"
PLANDIR="$RUN/plandir"                                                    # PD7f plan dir (census/core_conns/views) + event plan
PLAN="$PLANDIR/die_plan.json"

run() {  # print, or execute when DRY_RUN=0
  printf '+ %q ' "$@"; echo
  if [ "$DRY_RUN" = "0" ]; then "$@"; fi
}
otrun() {  # otrun MEM DIR -- cmd...
  local mem="$1" dir="$2"; shift 2; [ "$1" = "--" ] && shift
  run "${OTRUN[@]}" --mem "$mem" --dir "$dir" -- "$@"
}
note() { echo "# [$(date '+%F %T %Z')] $*"; }

stage_A() {  # plan event: one S81 event = svc13 band + PHY direct merge + ROWX=1 + bk_sel u_tx lattice fix
  note "A: plan event (ruling $RULING)"
  run ssh -o ControlPath=none intel1 "test \"\$(sha256sum $PLAN_IN | cut -c1-64)\" = $PLAN_SHA"   # input guard
  # TODO(T0): apply the ruled PLAN-DELTA (bk_sel u_tx origin y64.8 -> lattice; ROWX=1; QXPQ GB) with the owner's tool, no hand edits
  otrun 16 "$RUN" -- python3 "$TD/fallback_regions.py" plan "$PLAN" --lat "$PLANDIR/lat" --out "$RUN/regions" \
        --block 2 --mode class --core tap --groups "$RUN/phy_direct_groups.json"
  # landings recomposed with main clock_landing_plan.compose (dataflow monitor per FALLBACK-HEAD-3; thin-bank search)
  otrun 16 "$RUN" -- python3 -c "import sys; sys.path.insert(0,'$TD'); import clock_landing_plan as C; C.main_compose('$PLAN','$RUN/regions/landed_crossings.json','$RUN/compose')"  # TODO(T0): compose entry point name on SRC_SHA
  otrun 16 "$RUN" -- python3 "$TD/gen.py" latency "$RUN/compose/landed_plan.json" --inplace
  otrun 16 "$RUN" -- python3 "$TD/check.py" "$RUN/compose/landed_plan.json" --completeness --out "$RUN/g0"
  otrun 8  "$RUN" -- python3 "$TD/render.py" "$RUN/compose/landed_plan.json" --out "$RUN/render.png"
  note "A: STOP for G0 == ruled base set + GEOM review of render.png before B/C"
}

stage_B() {  # region clock trees + combined die GRT incl. clock, TT+FF, >=50 it
  note "B: region trees (equal trunk, sl300 slide, 405-um repeaters) + die GRT"
  otrun 32 "$RUN" -- python3 "$TD/die_trial.py" kit "$RUN/compose/landed_plan.json" --out "$RUN/kit" \
        --region-trees "$RUN/regions/regions.json" --htree-full-depth --tree-site-slide --leaf-um 300 --rep-um 405
  for C in TT FF; do   # measured max RSS 17.0 GB / ~4.4 min per corner (FALLBACK-S81-2, 10-26)
    otrun 24 "$RUN" -- bash -c "python3 $SRC/results/fallback_head_1026/scripts/mk_combo_dcm.py $RUN/kit $RUN/kit/clk $RUN/out_$C && cd $RUN/out_$C && openroad -exit combo.tcl > combo_$C.log 2>&1"  # TODO(T0): corner-specific combo tcl per FALLBACK-S81-2 mk_$C
  done
  # landed |d| <= 416.5 ps on every crossing (diagnostic) -- PATH-S81-PD land_report_regions.py
  otrun 8 "$RUN" -- python3 "$SRC/results/path_s81_pd_1026/scripts/land_report_regions.py" "$RUN" --out "$RUN/landed_report.json"  # TODO(T0): script on main after ROOT-MERGE
  note "B: STOP unless overflow 0 TT+FF and landed |d| PASS"
}

stage_C() {  # strict bind on the event plan (v10 OOM'd at 40 GB; 160 GB measured to complete)
  note "C: strict bind"
  otrun 160 "$RUN" -- python3 "$TD/bind.py" --strict --mem 160 --out "$RUN/bind" "$RUN/compose/landed_plan.json"  # TODO(T0): bind.py subcommand/args on SRC_SHA
}

stage_D() {  # 233 changed partition types: gen rtl/phys -> preflight -> autopilot (synth/LEC/G2/route/RCX/signoff/LEC)
  note "D: kits (LP slices first; 12 untouched types skipped; hard cores reused)"
  local TYPES="${TYPES_FILE:-$RUN/changed_types.txt}"   # from plan_summary / s81_type_build_est.json (233 rows)
  otrun 32 "$RUN" -- python3 "$TD/gen.py" rtl  "$RUN/compose/landed_plan.json" --out "$RUN/kits" --rtl-root "$SRC" --types "@$TYPES"
  otrun 32 "$RUN" -- python3 "$TD/gen.py" phys "$RUN/compose/landed_plan.json" --out "$RUN/kits" --rtl-root "$SRC" --types "@$TYPES"
  while read -r T; do
    mem=40
    case "$T" in dsdv_slice_*_LP*) mem=64;; svc_*) mem=48;; slice_station*) mem=32;; esac
    run ssh -o ControlPath=none intel1 python3 "$TD/kit_preflight.py" "$RUN/kits/$T" --out "$RUN/kits/$T/preflight.json"
    otrun "$mem" "$RUN/kits/$T" -- bash run_kit.sh   # autopilot picks it up after GEOM auto-pass (owner 10-27)
  done < <(ssh -o ControlPath=none intel1 cat "$TYPES" 2>/dev/null || true)
}

stage_E() {  # related-pair die STA, shared model (no fork): AOCV 0.21 %/mm, droop per region, hold buffers on data
  note "E: die_sta_related TT/FF on real views"
  # TODO(T0): export die_trial GRT arrivals to tap_arrivals_<C>.json (die_clock_mesh proof format) -- tool gap
  otrun 64 "$RUN" -- python3 "$TD/die_sta_related.py" "$RUN/proof" --plan "$RUN/compose/landed_plan.json" \
        --out "$RUN/sta" --corner TT --corner FF --clock-aocv-table "$TD/clk_aocv_table_g021.json" \
        --droop-regions "$RUN/regions/droop_regions.json" --hold-buffers "$RUN/hold_buffers.json"
  note "E: NUMBER-CHECK before any PASS claim"
}

note "S81 fallback, ruling=$RULING, DRY_RUN=$DRY_RUN, stages=$STAGES, src=$SRC_SHA"
for s in $STAGES; do "stage_$s"; done
