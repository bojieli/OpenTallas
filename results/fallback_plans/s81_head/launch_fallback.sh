#!/usr/bin/env bash
# s81_head landed bottom-up FALLBACK launch script -- UNEXECUTED (FALLBACK-PLAN-PREP-2, 2026-10-27).
# PLAN ONLY until the OWNER trigger: 2026-10-29 12:00 PDT, KV+QC related-pair die STA not both PASS.
# Usage: FALLBACK_TRIGGER=FIRED DRY_RUN=0 ./launch_fallback.sh <COORD-RULING-ID> <step|all>
#   steps: s0 s2 s3 s4 s6 s7  (s1 = tool code, done by a lane agent; s5 runs inside the s4 chains)
# DRY_RUN=1 (default) prints every command and runs nothing.
set -euo pipefail

RULING="${1:-}"; STEP="${2:-all}"
DRY_RUN="${DRY_RUN:-1}"
T0_EPOCH=$(TZ=America/Los_Angeles date -d '2026-10-29 12:00' +%s)
NOW=$(date +%s)
[[ "${FALLBACK_TRIGGER:-}" == "FIRED" ]] || { echo "REFUSED: FALLBACK_TRIGGER!=FIRED (owner trigger not fired)"; exit 2; }
(( NOW >= T0_EPOCH )) || { echo "REFUSED: before 2026-10-29 12:00 PDT"; exit 2; }
[[ "$RULING" =~ ^COORD- ]] || { echo "REFUSED: need a COORD ruling id (e.g. COORD-2026-10-29-1205-FALLBACK)"; exit 2; }

# ---- configuration (verify at launch; all tools are on main) ----
SRC_REF="${SRC_REF:?set SRC_REF = main sha carrying the final R18 HEAD plan + tools}"
R18_PLAN="${R18_PLAN:?set R18_PLAN = repo-relative final R18 s81_head die_plan.json}"
OBSERVER_SPEC="${OBSERVER_SPEC:-}"          # JSON {module,instance_suffix,fault_port,ready_port}; S1 output
RUN=/srv/opentallas-scratch2/claude/fallback-head-${SRC_REF:0:10}
HOSTS=(epyc2 intel1 intel2)                  # never epyc1 (retired 10-27)
OTRUN=(ssh -o ControlPath=none intel2 '~/.local/bin/ot-run')
LOG="$RUN/launch_$(date +%Y%m%d_%H%M%S).log"

run() { echo "+ $*"; [[ "$DRY_RUN" == "1" ]] || "$@"; }
otrun() { # otrun MEM NAME -- cmd...  (data dir staged on every host; ot-run picks by memory)
  local mem=$1 name=$2; shift 3
  run "${OTRUN[@]}" --mem "$mem" --dir "$RUN" -- bash -lc "cd $RUN/src && $* > $RUN/logs/$name.log 2>&1"
}
stage() { # create src snapshot of SRC_REF on every host (scratch only)
  for h in "${HOSTS[@]}"; do
    run ssh -o ControlPath=none "$h" "mkdir -p $RUN/logs && cd ~/OpenTallas && git fetch -q origin && \
      rm -rf $RUN/src && mkdir -p $RUN/src && git archive $SRC_REF | tar -x -C $RUN/src"
  done
}

s0() { # recompose landed topology on the final R18 plan + latency regen + G0/G0C (light, direct w/ memory cap)
  stage
  local P=results/fallback_plans/s81_head/r18
  run ssh -o ControlPath=none intel2 "cd $RUN/src && mkdir -p $P && \
    systemd-run --user --scope -q -p MemoryMax=8G python3 -I tools/s81_head/fallback_land.py plan $R18_PLAN --out $P/regions --granularity part && \
    systemd-run --user --scope -q -p MemoryMax=8G python3 -I tools/s81_head/fallback_land.py compose $R18_PLAN \
      --table $P/regions/regions_part.json --out $P/compose --monitor dataflow ${OBSERVER_SPEC:+--observer-spec $OBSERVER_SPEC} && \
    systemd-run --user --scope -q -p MemoryMax=8G python3 -I tools/die_plan/gen.py latency $P/compose/landed_plan.json --inplace --out $P/lat && \
    systemd-run --user --scope -q -p MemoryMax=8G python3 -I tools/die_plan/check.py $P/compose/landed_plan.json --completeness --out $P/g0"
  echo "S0 GATE: G0C must equal the base error set (0E on 10-27); 0 storage-band FAIL; 0 type splits; landing_contract 0 errors"
}

s2() { # die tree (sl300 recipe) on R18 + reserved sites
  local P=results/fallback_plans/s81_head/r18
  otrun 8 die_tree -- python3 -I tools/die_plan/die_trial.py kit $P/compose/landed_plan.json --out $RUN/tree \
      --leaf-um 300 --htree-full-depth --tree-site-legal --tree-site-slide
  otrun 8 reserve -- python3 -I tools/s81_head/fallback_reserve.py $P/compose/landed_plan.json $RUN/tree/tree.json \
      $P/compose/landed_sidecar.json --out $P/reserved_plan.json --report $P/reserve_report.json
  echo "S2 GATE: 0 tree cells on hard cores / VDDPHY / outside partitions; GEOM auto check on tree render"
}

s3() { # kits for all 16 types (requires S1 strict bind PASS)
  [[ -n "${STRICT_BIND_OK:-}" ]] || { echo "BLOCKED: S1 (binder ring emission + observer + 8-FT adapter) strict bind receipt required: set STRICT_BIND_OK=<bind.json>"; exit 3; }
  local P=results/fallback_plans/s81_head/r18
  otrun 16 gen_rtl -- python3 -I tools/die_plan/gen.py rtl $P/reserved_plan.json --out $RUN/rtl --rtl-root .
  otrun 16 gen_phys -- python3 -I tools/die_plan/gen.py phys $P/reserved_plan.json --out $RUN/kits --rtl-root . --hold-mcmm
  for t in hd_tile hd_turn_a hd_turn_b hd_spn hd_spn_end hd_serdes hd_st_turn hd_st_str hd_st_n3 hd_st_n4 hd_st_m hd_st_k5 hd_mesh hd_lep0N hd_ctl hd_host; do
    otrun 4 "preflight_$t" -- python3 -I tools/die_plan/kit_preflight.py $RUN/kits/$t --out $RUN/kits/$t/preflight.json
  done
  echo "S3 GATE: 16/16 preflight PASS; AUTO GEOM PASS (1-in-5 visual)"
}

s4() { # 16 type builds -> signoff + routed LEC via the AUTOPILOT-SIGNOFF chain (kit run_kit.sh)
  declare -A MEM=([hd_tile]=32 [hd_turn_a]=24 [hd_turn_b]=24 [hd_spn]=24 [hd_spn_end]=24 [hd_serdes]=16 \
    [hd_st_turn]=16 [hd_st_str]=16 [hd_st_n3]=16 [hd_st_n4]=16 [hd_st_m]=16 [hd_st_k5]=16 \
    [hd_mesh]=32 [hd_lep0N]=48 [hd_ctl]=48 [hd_host]=40)
  [[ -n "${ELEM_VIEWS_SIGNED:-}" ]] || echo "WARN: hd_tile waits for signed elemA/elemB views (ELEM_VIEWS_SIGNED unset) -- skipping hd_tile"
  for t in "${!MEM[@]}"; do
    [[ "$t" == hd_tile && -z "${ELEM_VIEWS_SIGNED:-}" ]] && continue
    otrun "${MEM[$t]}" "build_$t" -- bash $RUN/kits/$t/run_kit.sh
  done
  echo "S4/S5 GATE: signoff.py SIGNED + routed LEC EQ per type; clock_landing ring-window STA PASS per landed type"
}

s6() { # die GRT incl clock >= 50 iterations, TT and FF
  local P=results/fallback_plans/s81_head/r18
  for c in TT FF; do
    run "${OTRUN[@]}" --priority die --mem 64 --dir "$RUN" -- bash -lc "cd $RUN/src && python3 -I tools/die_plan/die_infra.py grt \
      $P/reserved_plan.json --kit $RUN/tree --pre $RUN/tree --out $RUN/grt_$c > $RUN/logs/grt_$c.log 2>&1"
  done
  echo "S6 GATE: overflow 0 at >= 50 iterations TT+FF (12.4a)"
}

s7() { # related-pair die STA, shared model, real views
  local P=results/fallback_plans/s81_head/r18
  run "${OTRUN[@]}" --priority die --mem 32 --dir "$RUN" -- bash -lc "cd $RUN/src && python3 -I tools/die_plan/die_sta_related.py \
    --plan $P/reserved_plan.json --out $RUN/die_sta --corner TT --corner FF --clock-tool tools/die_plan \
    --core-view-match-pins --droop-region mesh --landing-window-ps 416.5 --hold-buffers \
    ${CORE_VIEWS:?set CORE_VIEWS='--core-view MOD=DIR ...'} ${KITS:?set KITS='--kit type=kit.json ...'} > $RUN/logs/die_sta.log 2>&1"
  echo "S7 GATE: TT setup >= 0, FF hold >= 0 on all related pairs (AOCV 0.21%/mm default table); then NUMBER-CHECK"
}

echo "s81_head fallback ruling=$RULING step=$STEP DRY_RUN=$DRY_RUN src=$SRC_REF $(date)"
case "$STEP" in
  s0|s2|s3|s4|s6|s7) "$STEP" ;;
  all) s0; s2; s3; s4; echo "after S4/S5 complete: rerun with step s6 then s7" ;;
  *) echo "unknown step $STEP"; exit 2 ;;
esac
