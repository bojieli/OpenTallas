#!/bin/bash
# Fleet entry point: assemble -> compile/replay -> head/MTP -> calendar -> report.
# Run with ot-run. All fixtures are existing checkpoint-derived fixture directories.
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd)
REF=; WORK=; FIX=; DIE=; PB=; PLAN=; LAND=; REPORT=0; ASM=; SRC=
HEAD_PREP=; HEAD_FIX=; MU_STAGE=; HEAD_JSON=; MU_JSON=; LAYERS_JSON=
CAL_AR=; CAL_MTP=; MU_LINK_JSON=
FOLD_JSON=
KV_BASELINE=; KV_JSON=; DENSE_VECTORS=; DENSE_JSON=
ENTRY_NORM_JSON=; AGGREGATE_SOURCE_JSON=; ENTRY_PRODUCER_JSON=
# Native entry HOST jobs on a BUILT u_seqhost cut (cut_3S_ctl): kit, obj (with sim), idle run, replay progs, fixture meta.
ENTRY_KIT=; ENTRY_OBJ=; ENTRY_IDLE=; ENTRY_PROGS=; ENTRY_META=; ENTRY_USER=0; ENTRY_REPLAY_JSON=
LADDER_JSON=$(cd "$(dirname "$0")/../../.." && pwd)/results/token_pass/tokfunc3_s81_1021/ladder.json
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
    --kv-baseline) KV_BASELINE=$2; shift 2;; --kv-json) KV_JSON=$2; shift 2;;
    --dense-source-vectors) DENSE_VECTORS=$2; shift 2;; --dense-source-json) DENSE_JSON=$2; shift 2;;
    --entry-norm-json) ENTRY_NORM_JSON=$2; shift 2;;
    --aggregate-source-json) AGGREGATE_SOURCE_JSON=$2; shift 2;;
    --entry-producer-json) ENTRY_PRODUCER_JSON=$2; shift 2;;
    --entry-kit) ENTRY_KIT=$2; shift 2;; --entry-obj) ENTRY_OBJ=$2; shift 2;;
    --entry-idle) ENTRY_IDLE=$2; shift 2;; --entry-progs) ENTRY_PROGS=$2; shift 2;;
    --entry-meta) ENTRY_META=$2; shift 2;; --entry-user) ENTRY_USER=$2; shift 2;;
    --entry-replay-json) ENTRY_REPLAY_JSON=$2; shift 2;;
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
  if [ -n "$ENTRY_OBJ" ] && [ -n "$ENTRY_PROGS" ]; then
    # Consumes an existing cut binary; never builds (a live build is not duplicated).  Mutant: corrupted host header.
    python3 "$H/run_entry_replay.py" --src "$SRC" --die-v "$WORK/tree/results/arch/s81_dv_1016/bind9/die.v.gz" --cut "$WORK/cuts/cut_3S_ctl" --kit "$ENTRY_KIT" \
      --obj "$ENTRY_OBJ" --idle-run "$ENTRY_IDLE" --progs "$ENTRY_PROGS" --fixture-meta "$ENTRY_META" \
      --ks-user "$ENTRY_USER" --out "$WORK/entry_replay" --mutant 15:corrupt:hf_7N_l0:13 > "$WORK/entry_replay.log" 2>&1 || true
    ENTRY_REPLAY_JSON=$WORK/entry_replay/entry_replay.json
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
[ -z "$ENTRY_NORM_JSON" ] || ARGS+=(--entry-norm "$ENTRY_NORM_JSON")
[ -z "$AGGREGATE_SOURCE_JSON" ] || ARGS+=(--aggregate-source "$AGGREGATE_SOURCE_JSON")
[ -z "$ENTRY_PRODUCER_JSON" ] || ARGS+=(--entry-producer "$ENTRY_PRODUCER_JSON")
[ -z "$ENTRY_REPLAY_JSON" ] || ARGS+=(--entry-replay "$ENTRY_REPLAY_JSON")
[ ! -f "$LADDER_JSON" ] || ARGS+=(--ladder "$LADDER_JSON")
[ -z "$DIE" ] || ARGS+=(--die-v "$DIE")
python3 "$H/token_report.py" "${ARGS[@]}"
