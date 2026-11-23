#!/bin/bash
# HEAD-BIND-1 11-14: s81_head die bind + LATCHECK driver (one job; run it under ot-run --priority plan).
#
# HEAD has no as-built GEN die top: its kit RTL is the plan's own generated wrappers (gen.py phys bootstrap +
# reset-alias patch, wave-prepared published/ cohort).  The HEAD as-built die is therefore the gen.py rtl composition
# of the SAME prepared plan + sidecar, and the die bind is:
#   1. COHORT   tools/s81_head/head_gen_cohort.py: every published kit wrapper == alias_patch(gen.py rtl wrapper)
#   2. BIND     tools/s81_head/head_die_portbind.py --clock-landing: strict die port-bind (die_port_bind --manifest-only,
#               module check, tie audit, nested leaf-pin check) of the landed die top s81_head_top
#   3. LATCHECK tools/die_plan/gen_lane_latcheck.py --fixed-in-core: lane_asbuilt_latency.check on the published
#               wrappers (+ gen output), landing cycles from gen_clock_landings.json, lane fixed_cycles in the cores
#
# usage: head_bind_latcheck.sh TAG PREPARED_DIR
#   PREPARED_DIR = a HEAD wave-prepared dir (source_plan.json, source_sidecar.json, published/, wave_prepare.json)
#   env SRC   code tree (default the kw45 HEAD wave src); hardlinked into the run tree, never written
#       TOOLS tools overlay root whose tools/die_plan + tools/s81_head files replace the tree's (default: this repo)
#       RUN   run root (default /srv/opentallas-scratch2/claude/head-bind-1/run); the run dir is RUN/TAG (must not exist)
#       BASE_PREP  LATCHECK-REALIZED-1122: the plan-of-record prepared dir (source_plan.json + published/); LATCHECK then
#             refuses station rows / lane cycles that change no RTL (UNREALIZED_STATION_ROW / UNREALIZED_PLAN_CYCLES)
# exit: 0 all PASS, 3 run dir exists, 4 cohort FAIL, 5 bind FAIL, 6 LATCHECK FAIL (lane latency), 7 LATCHECK incomplete
set -u -o pipefail
TAG=$1; PREP=$(readlink -f "$2")
SRC=${SRC:-/srv/opentallas-scratch2/claude/kw45/src_head_rp21z_pgcaplec_c327}
TOOLS=${TOOLS:-$(cd "$(dirname "$0")/../.." && pwd)}
RUN=${RUN:-/srv/opentallas-scratch2/claude/head-bind-1/run}
R=$RUN/$TAG; D=$R/src; O=results/head_bind/$TAG
export PYTHONDONTWRITEBYTECODE=1
test ! -e "$R" || { echo "REFUSE $R exists"; exit 3; }
for f in source_plan.json source_sidecar.json; do test -s "$PREP/$f" || { echo "MISSING $PREP/$f"; exit 2; }; done
test -d "$PREP/published" || { echo "MISSING $PREP/published"; exit 2; }
mkdir -p "$D"
# FLOW-OPS-1000 (FABLE-FLOW-1000 c): a sealed published tree (.src-manifest.json) is copied, never hardlinked into a private run
LNK=-al; [ -e "$SRC/.src-manifest.json" ] && LNK="-a --reflink=auto"
for d in $(ls -A "$SRC"); do [ "$d" = results ] || cp $LNK "$SRC/$d" "$D/"; done
for f in tools/die_plan/gen_lane_latcheck.py tools/die_plan/lane_asbuilt_latency.py tools/die_plan/core_latency.py \
         tools/die_plan/count_frame.py tools/die_plan/port_bind_gate.py tools/s81_head/head_die_portbind.py tools/s81_head/head_module_check.py \
         tools/s81_head/head_gen_cohort.py; do
  cp --remove-destination "$TOOLS/$f" "$D/$f" || exit 2
done
echo "plan $(sha256sum < "$PREP/source_plan.json" | cut -c1-12) sidecar $(sha256sum < "$PREP/source_sidecar.json" | cut -c1-12) src $SRC tools $(git -C "$TOOLS" rev-parse --short HEAD 2>/dev/null)"
cd "$D" || exit 9
mkdir -p "$O"
python3 -I -B tools/s81_head/head_die_portbind.py "$PREP/source_plan.json" --clock-landing "$PREP/source_sidecar.json" --out "$O" > "$R/bind.log" 2>&1
BRC=$?; echo "BIND_RC=$BRC $(grep -h '^HEAD_DIE_PORTBIND' "$R/bind.log" | tail -1)"
test -s "$O/gen/s81_head_top.sv" || { echo "NO_GEN_TOP"; tail -5 "$R/bind.log"; exit 5; }
python3 -I -B tools/s81_head/head_gen_cohort.py "$PREP" "$O/gen" --json "$R/cohort.json" > "$R/cohort.log" 2>&1
CRC=$?; echo "COHORT_RC=$CRC $(tail -1 "$R/cohort.log")"
python3 -I -B tools/die_plan/gen_lane_latcheck.py "$PREP/source_plan.json" --rtl "$PREP/published" --rtl "$O/gen" \
  --landings "$O/gen/gen_clock_landings.json" --fixed-in-core \
  ${BASE_PREP:+--base-plan "$BASE_PREP/source_plan.json" --base-rtl "$BASE_PREP/published"} --tsv "$R/latcheck.tsv" --json "$R/latcheck.json" > "$R/latcheck.log" 2>&1
LRC=$?; echo "LATCHECK_RC=$LRC $(tail -1 "$R/latcheck.log" | cut -c1-300)"
ln -sfn "$D/$O" "$R/out"
echo "HEAD_BIND_DONE bind=$BRC cohort=$CRC latcheck=$LRC out=$R"
[ $CRC = 0 ] || exit 4
[ $BRC = 0 ] || exit 5
[ $LRC = 0 ] || { [ $LRC = 5 ] && exit 7; exit 6; }
exit 0
