#!/bin/bash
# TOK-FUNC-S81 step 3 (fleet): compile the layer programmes on the 72-frame RTL assembly die tree, in parallel.
#   compile_layers.sh <root> <tree> <fixtures dir> <out dir> [LAYER ...]
# <root> = git archive of claude/tokfunc-s81-1021 (tools rtl compiler/models/deepseek-v4.1-flash results/arch/token_path_20261009
# results/arch/s81_dv_1016 results/arch/s81_map72_1021 results/token_pass); <tree> = mk_tree.py output; fixtures
# <fix>/<L0|L2|L14|L20|HEAD|MTP> (dv_layer_fixtures.py, manifests results/rtl/s81_layer_tput_1018/fixtures).
# LAYER: L0 L2 L14 L20 (single user, --fixtures) and L0:mu etc. (multi-user: --mu-cal <out>/mu_cal.json --mu-ctx).
set -u
ROOT=$(realpath $1); T=$(realpath $2); F=$(realpath $3); O=$(realpath -m $4); shift 4
LAYERS=${*:-L0 L2 L14 L20}
mkdir -p $O
cd "$ROOT"
# LP parents add per-path ages: never compile against stale flat/archive timing.
# Explicit caller models remain subject to lower_xs source-hash validation.
if [ -z "${OT_XS_FRAME_SCHEDULE_DIR:-}" ]; then
  python3 tools/s81_dv/tokfunc/prepare_frame_schedules.py --tree "$T" --out "$O/frame_schedules" \
    > "$O/frame_schedules.log" 2>&1 || exit $?
  export OT_XS_FRAME_SCHEDULE_DIR="$O/frame_schedules"
fi
# Every invocation names the engine calendar. An explicit override still passes
# the compiler's selected-source check; absent override derive it from the
# caller's actual bind define set.
PROFILE=${OT_SVC_TIMING_PROFILE:-}
if [ -z "$PROFILE" ]; then
  case ",${OT_S81_SELECTED_DEFINES:-}," in
    *,SVCQ_ENG_FG3,*) PROFILE=legacy_fg3 ;;
    *) PROFILE=closing_allq ;;
  esac
fi
if [ "$PROFILE" = closing_allq ]; then
  : "${OT_SVC_ALLQ:=1}" "${OT_SVC_SMT:=1}"
  export OT_SVC_ALLQ OT_SVC_SMT
fi
for L in $LAYERS; do
  base=${L%%:*}; mode=${L#*:}; [ "$mode" = "$L" ] && mode=su
  args=(--layer $base --out $O/prog_${base}_$mode --die-src $T --svc-timing-profile "$PROFILE")
  [ -d $F/$base ] && args+=(--fixtures $F/$base)
  if [ "$mode" = mu ]; then args+=(--mu-cal $O/mu_cal.json --mu-ctx); fi
  ( /usr/bin/time -v -o $O/cc_${base}_$mode.time python3 tools/s81_dv/dv_layer_compile.py "${args[@]}" > $O/cc_${base}_$mode.log 2> $O/cc_${base}_$mode.err
    echo "CC $L rc $? $(tail -n 2 $O/cc_${base}_$mode.log | head -1 | cut -c1-200)" ) &
done
wait
