#!/bin/bash
# Fleet entry point: assemble -> compile/replay -> head/MTP -> calendar -> report.
# Run with ot-run. All fixtures are existing checkpoint-derived fixture directories.
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd)
REF=; WORK=; FIX=; DIE=; PB=; PLAN=; LAND=; REPORT=0; ASM=; SRC=
HEAD_PREP=; HEAD_FIX=; MU_STAGE=; HEAD_JSON=; MU_JSON=; LAYERS_JSON=
CAL_AR=; CAL_MTP=; MU_LINK_JSON=
FOLD_JSON=
HEAD_DIE_SRC=; HEAD_DIE_BIND=; HEAD_DIE_IMG=; HEAD_DIE_JSON=; GAPS_JSON=
KV_BASELINE=; KV_JSON=; DENSE_VECTORS=; DENSE_JSON=
while (($#)); do
  case "$1" in
    --ref) REF=$2; shift 2;; --work) WORK=$2; shift 2;;
    --fixtures) FIX=$2; shift 2;; --die-v) DIE=$2; shift 2;;
    --port-bind) PB=$2; shift 2;; --plan) PLAN=$2; shift 2;;
    --land) LAND=$2; shift 2;; --assembly-dir) ASM=$2; shift 2;;
    --source-root) SRC=$2; shift 2;; --head-prep) HEAD_PREP=$2; shift 2;;
    --head-fixtures) HEAD_FIX=$2; shift 2;; --mu-stage) MU_STAGE=$2; shift 2;;
    --head-json) HEAD_JSON=$2; shift 2;; --mu-json) MU_JSON=$2; shift 2;;
    --mu-link-json) MU_LINK_JSON=$2; shift 2;;
    --layers-json) LAYERS_JSON=$2; shift 2;; --report-only) REPORT=1; shift;;
    --calendar-ar) CAL_AR=$2; shift 2;; --calendar-mtp) CAL_MTP=$2; shift 2;;
    --owner-fold-json) FOLD_JSON=$2; shift 2;;
    --head-die-src) HEAD_DIE_SRC=$2; shift 2;; --head-die-bind) HEAD_DIE_BIND=$2; shift 2;;
    --head-die-img) HEAD_DIE_IMG=$2; shift 2;; --head-die-json) HEAD_DIE_JSON=$2; shift 2;;
    --layer-gaps-json) GAPS_JSON=$2; shift 2;;
    --kv-baseline) KV_BASELINE=$2; shift 2;; --kv-json) KV_JSON=$2; shift 2;;
    --dense-source-vectors) DENSE_VECTORS=$2; shift 2;; --dense-source-json) DENSE_JSON=$2; shift 2;;
    *) echo "unknown argument: $1" >&2; exit 2;;
  esac
done
: "${REF:?--ref required}" "${WORK:?--work required}"
mkdir -p "$WORK"
GRADE=source; [ -z "$DIE" ] || GRADE=netlist
if [ "$REPORT" = 0 ]; then
  : "${FIX:?--fixtures required}"
  ASM=${ASM:-$WORK/assembly}
  if [ -z "$DIE" ]; then
    # An existing assembly is reused only after its strict bind completed.
    if ! grep -q '^BIND_RC 0 ' "$ASM/steps.log" 2>/dev/null; then
      if [ -e "$ASM/steps.log" ]; then
        echo "Existing assembly has no successful strict bind; preserve it and use a fresh --work or --assembly-dir" >&2
        exit 3
      fi
      bash "$H/assemble_rtl72.sh" "$REF" "$ASM" > "$WORK/assembly.log" 2>&1
    fi
    ACTUAL_REF=$(awk '$1 == "REF" {print $2; exit}' "$ASM/snapshot.refs")
    G=${OT_GIT_DIR:-/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git}
    EXPECTED_REF=$(git --git-dir="$G" rev-parse "$REF^{commit}")
    if [ "$ACTUAL_REF" != "$EXPECTED_REF" ]; then
      echo "Assembly source ref differs from --ref; preserve existing assembly and use a fresh work directory" >&2
      exit 3
    fi
    DIE=$ASM/bind/bind/die.v; PB=$ASM/bind/bind/port_bind.json
    PLAN=$ASM/plan_routed_g7.json; LAND=$ASM/land_plan_g7.json
  else
    : "${PB:?--port-bind required with --die-v}" "${PLAN:?--plan required with --die-v}" "${LAND:?--land required with --die-v}"
  fi
  SRC=${SRC:-$ASM/src}
  python3 "$H/mk_tree.py" --die-v "$DIE" --plan "$PLAN" --land "$LAND" --out "$WORK/tree" > "$WORK/tree.log" 2>&1
  # Replay runner retains failed compiler/replay receipts; no blanket success.
  bash "$H/compile_layers.sh" "$SRC" "$WORK/tree" "$FIX" "$WORK/layers" > "$WORK/compile.log" 2>&1
  bash "$H/prep_cuts.sh" "$REF" "$DIE" "$PB" "$LAND" "$WORK" > "$WORK/cuts.log" 2>&1
  if [ -f "$H/run_layers.sh" ]; then
    CUT_ROOT=$WORK bash "$H/run_layers.sh" "$SRC" "$WORK/tree" "$FIX" "$WORK/layers" > "$WORK/replay.log" 2>&1 || true
    LAYERS_JSON=$WORK/layers/layers_report.json
  fi
  bash "$H/run_owner_fold.sh" "$SRC" "$WORK/owner_fold" > "$WORK/owner_fold.log" 2>&1 || true
  FOLD_JSON=$WORK/owner_fold/receipt.json
  if [ -n "$KV_BASELINE" ]; then
    python3 "$SRC/tools/s81_dv/kv_vp_1021/gate.py" --baseline "$KV_BASELINE" --out "$WORK/kv_consumer" \
      --jobs "${J:-2}" > "$WORK/kv_consumer.log" 2>&1 || true
    KV_JSON=$WORK/kv_consumer/result.json
  fi
  if [ -n "$DENSE_VECTORS" ]; then
    (cd "$SRC"; bash tools/s81_dv/tokfunc/run_dense_xs_cap.sh "$WORK/dense_source" "$DENSE_VECTORS") \
      > "$WORK/dense_source.log" 2>&1 || true
    DENSE_JSON=$WORK/dense_source/check.json
  fi
  # LAYER.2-4 GAP classes against the die.v the layers compiled on (TOK-FUNC2-S81-LX gap_classify.py)
  LW=(); for L in L2 L14 L20; do [ -f "$WORK/layers/prog_${L}_su/lowering.json" ] && LW+=("$WORK/layers/prog_${L}_su/lowering.json"); done
  if [ ${#LW[@]} -gt 0 ]; then
    python3 "$H/gap_classify.py" --die-v "$DIE" --lowering "${LW[@]}" --out "$WORK/layer_gaps.json" > "$WORK/layer_gaps.log" 2>&1 || true
    GAPS_JSON=$WORK/layer_gaps.json
  fi
  # LAYER.5: the LM head on the whole bound head die (its own bind: --head-die-bind = strict-bind dir of the head die
  # GEN or source assembly; images from head_die_images.py).  At closure pass the head die GEN bind dir here.
  if [ -n "$HEAD_DIE_SRC" ] && [ -n "$HEAD_DIE_BIND" ] && [ -n "$HEAD_DIE_IMG" ]; then
    bash "$H/head_die/run_head_die.sh" "$HEAD_DIE_SRC" "$HEAD_DIE_BIND" "$HEAD_DIE_IMG" "$WORK/head_die" > "$WORK/head_die.log" 2>&1 || true
    HEAD_DIE_JSON=$WORK/head_die/result.json
  fi
  # These component benches use their source-pinned RTL, even in netlist mode.
  if [ -n "$HEAD_PREP" ] && [ -n "$HEAD_FIX" ]; then
    (cd "$SRC"; bash "$H/head_mtp_fleet.sh" "$HEAD_PREP" "$HEAD_FIX" "$WORK/head") > "$WORK/head.log" 2>&1 || true
    python3 "$H/head_mtp_report.py" --run "$WORK/head" --prep "$HEAD_PREP" --out "$WORK/head.json"
    HEAD_JSON=$WORK/head.json
  fi
  if [ -n "$MU_STAGE" ]; then
    # A source-pinned endpoint stage prepared by tools/xdie_s81_2/stage.sh.
    (cd "$MU_STAGE"; bash "$H/mu_fleet.sh" build) > "$WORK/mu_build.log" 2>&1 || true
    if [ -f "$MU_STAGE/out/DONE_build" ]; then
      for c in su ar50r mtp10r ar50d mtp10d; do
        (cd "$MU_STAGE"; bash "$H/mu_fleet.sh" run "$c") > "$WORK/mu_$c.log" 2>&1 || true
      done
    fi
    CA=(); [ -z "$CAL_AR" ] || CA+=(--calendar-ar "$CAL_AR")
    [ -z "$CAL_MTP" ] || CA+=(--calendar-mtp "$CAL_MTP")
    python3 "$H/mu_collect.py" --out-dir "$MU_STAGE/out" --plans "$MU_STAGE/plans" --sources "$MU_STAGE/SOURCES.txt" --json "$WORK/mu.json" "${CA[@]}"
    MU_JSON=$WORK/mu.json
  fi
fi
ARGS=(--work "$WORK" --out "$WORK/token.json" --grade "$GRADE" --ref "$REF")
[ -z "$HEAD_JSON" ] || ARGS+=(--head "$HEAD_JSON")
[ -z "$MU_JSON" ] || ARGS+=(--mu "$MU_JSON")
[ -z "$MU_LINK_JSON" ] || ARGS+=(--mu-link "$MU_LINK_JSON")
[ -z "$LAYERS_JSON" ] || ARGS+=(--layers "$LAYERS_JSON")
[ -z "$FOLD_JSON" ] || ARGS+=(--owner-fold "$FOLD_JSON")
[ -z "$KV_JSON" ] || ARGS+=(--kv-consumer "$KV_JSON")
[ -z "$DENSE_JSON" ] || ARGS+=(--dense-source "$DENSE_JSON")
[ -z "$HEAD_DIE_JSON" ] || ARGS+=(--head-die "$HEAD_DIE_JSON")
[ -z "$GAPS_JSON" ] || ARGS+=(--layer-gaps "$GAPS_JSON")
[ -z "$DIE" ] || ARGS+=(--die-v "$DIE")
python3 "$H/token_report.py" "${ARGS[@]}"
