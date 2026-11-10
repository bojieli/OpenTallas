#!/bin/bash
# FLOW-CLOCK-R7 2026-10-29: run the shared post-route drive repair from a prd_mk.sh pass dir, at most 2 passes:
#   pass p: [two-mode patch] do-route (GRT + prd_hook.tcl ECO on the routed SPEF + ONE detailed route + fill)
#           -> clk_freeze_check.sh (blocking, as every ECO chain) -> RCX re-extraction + slew/cap count at TC and BC
#   slew+cap = 0 or p = 2 -> do-finish in that pass dir, then the kit's own GOAL=post sign-off (run_kit_hbm.sh /
#   run_kit_kv.sh / run_kit.sh when the kit has one; else the die owner signs off the pass dir);
#   otherwise pass p+1 = prd_mk.sh from pass p's 5_1_grt.odb + its RCX SPEF in D_p<p+1>.
#   prd_run.sh D [CPUS=8] [MEM_GB=32] [MAX_PASS=2]          (heavy: through ot-run --mem MEM_GB --dir D)
#   OT_PRD_FROM (from D/variant.env, prd_mk.sh): route = route-keeping ECO (pass p+1 again starts from pass p's routed DB)
#   final = route seeded with the kit's 6_final.odb (pass p+1 is route: pass p has no post-route edits)
#   OT_PRD_POST=0: skip the kit runner's GOAL=post sign-off after do-finish (default 1 = unchanged)
# Result: D/prd_result.json (per pass: rc, clk check, TC/BC slew + cap counts, sink masters restored; final dir).
set -uo pipefail
D0=$(cd "$1" && pwd); CPUS=${2:-8}; MEM=${3:-32}; MAXP=${4:-2}
HERE=$(cd "$(dirname "$0")" && pwd)
IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}
DK=docker; docker ps >/dev/null 2>&1 || DK="sudo docker"
# KW-FIX-44 11-10 (COORD): the pass / finish containers run as root (they patch ORFS inside the image) and chown /work
# when they end; a prd_run.sh stopped mid-pass left their outputs root-owned (HEAD-92 hd_spn_end i1t).  On EXIT / TERM /
# INT the current pass dir and the finish dir get the same root chown, only when a file there is not ours.  SIGKILL
# is not covered.  TERM keeps rc 143 (eco_loop: stopped from outside), INT 130.
prd_own_back() {
  local d
  for d in "${D:-}" "${FINAL:-}"; do
    [ -n "$d" ] && [ -d "$d" ] || continue
    [ -n "$(find "$d" ! -user "$(id -u)" -print -quit 2>/dev/null)" ] || continue
    $DK run --rm -v "$d":/work "$IMAGE" chown -R "$(id -u):$(id -g)" /work >/dev/null 2>&1 || true
  done
}
trap prd_own_back EXIT
trap 'prd_own_back; trap - EXIT; exit 143' TERM
trap 'prd_own_back; trap - EXIT; exit 130' INT
SO=$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["signoff_tools"])' $D0/PRD.json)
V=$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["variant"])' $D0/PRD.json)
RES=$D0/prd_result.json; [ -n "${OT_PRD_FINAL_ONLY:-}" ] && RES=$D0/prd_result_final.json
echo '{"passes": []}' > $RES
addres() { python3 -I - "$RES" "$@" <<'PY'
import json, sys
p, kv = sys.argv[1], sys.argv[2:]
r = json.load(open(p)); e = dict(a.split('=', 1) for a in kv)
if 'final' in e: r['final'] = e
else: r['passes'].append(e)
json.dump(r, open(p, 'w'), indent=1)
PY
}
count() {  # D TAG CORNER(TC|BC) SPEF CHKPL
  local D=$1 B count_mem count_cpus limits; B=$(ls -d $D/run/results/asap7/*/base)
  # The count subprocess stays inside the caller's admitted resource envelope.
  # Preserve the historical 24 GB / 4-thread ceiling for larger route requests.
  limits=$(python3 -I - "$MEM" "$CPUS" <<'PY_COUNT_LIMITS'
import math, sys
mem, cpus = float(sys.argv[1]), int(sys.argv[2])
if not math.isfinite(mem) or mem <= 0 or cpus <= 0:
    raise SystemExit("PRD count resources must be finite and positive")
print(f"{min(mem,24):g} {min(cpus,4)}")
PY_COUNT_LIMITS
  ) || return 2
  read -r count_mem count_cpus <<< "$limits"
  # KW-FIX-44 11-10 (COORD): the count container runs as the host user, so a SPEF it extracts into /work is not
  # root-owned (it has no chown after it).  The pass and finish containers stay root: they patch ORFS scripts inside
  # the image (orfs_hold_mm.py on every two-mode kit, kwrs_busfit.py on util.tcl), which are root 0664 there, so
  # --user would end them 'exit 9'; their output is chowned back by the container itself and by the chown run after.
  $DK run --rm --user="$(id -u):$(id -g)" --name prd-count-$2-$$ --cpus="$count_cpus" --memory="${count_mem}g" --memory-swap="${count_mem}g" -v "$D":/work -w /OpenROAD-flow-scripts/flow \
    -e ODB=/work/${B#$D/}/$(test -s $B/5_route.odb && echo 5_route.odb || echo 5_2_route.odb) -e SDC=/work/${B#$D/}/4_cts.sdc -e SPEF=/work/${B#$D/}/$4 -e TAG=$2 -e CHKPL=$5 "$IMAGE" bash -lc '
    source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
    M="make -s DESIGN_CONFIG=/work/config.mk WORK_HOME=/tmp/w FLOW_VARIANT=base"
    pv() { $M print-$1 2>/dev/null | sed "s/^[A-Z_]*: //"; }
    export OT_LIBS="$(pv '$3'_LIB_FILES)" RCX_RULES="$(pv RCX_RULES)" OT_LEFS="$(pv TECH_LEF) $(pv SC_LEF) $(pv ADDITIONAL_LEFS)"
    openroad -no_init -exit /work/prd_count.tcl' > $D/prd_count_$2.log 2>&1
  grep -h '^OT_PRD_COUNT' $D/prd_count_$2.log | tail -n 1
}
# KW-FIX-5 11-04: a kit whose child LEF has pins with no liberty port (all_registers segfaults on them): fit libs in the pass dir,
# OpenROAD reads them, and signoff.py finds them by the same K/.busfit path
busfit_prep() {
  [ -n "${OT_BUSFIT_PY:-}" ] && [ -f "$OT_BUSFIT_PY" ] || return 0
  cp "$OT_BUSFIT_PY" "$1/kwrs_busfit.py" && python3 -I "$1/kwrs_busfit.py" fit "$1"
  PATCH="python3 -I /work/kwrs_busfit.py patch /OpenROAD-flow-scripts/flow/scripts/util.tcl; $PATCH"
}
D=$D0; P=1; FINAL=; rc=0
# OT_PRD_FINAL_ONLY=<pass dir>: that pass already measured clean (prd_result.json); run only its finish + sign-off
if [ -n "${OT_PRD_FINAL_ONLY:-}" ]; then
  FINAL=$(cd "$OT_PRD_FINAL_ONLY" && pwd); . $FINAL/variant.env
  PATCH=true; [ "${OT_HOLD_MM_KIT:-0}" = 1 ] && PATCH="python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1 || exit 9"
  busfit_prep "$FINAL"
fi
while [ -z "${OT_PRD_FINAL_ONLY:-}" ]; do
  OT_PRD_FROM=grt; OT_PRD_PROTECT_NETS=; OT_PRD_NARROW_PINS=; OT_PRD_REPAIR_RC=; OT_PRD_AUTO_FANOUT=; OT_HOLD_REPAIR_SCOPE=; . $D/variant.env   # the pinned pass dir decides, not a stray export
  NAME=prd-$(basename $(dirname $D) | cut -c1-30)-$(basename $D)-$$
  PATCH=true; [ "${OT_HOLD_MM_KIT:-0}" = 1 ] && PATCH="python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1 || exit 9"
  busfit_prep "$D"
  $DK run --rm --name "$NAME" --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$D":/work \
    -e HUID=$(id -u) -e HGID=$(id -g) -e OT_PRD_PASS=$P -e OT_PRD_TARGETED=${OT_PRD_TARGETED:-0} -e OT_PRD_LOCAL_BRANCHES=${OT_PRD_LOCAL_BRANCHES:-} ${OT_PRD_LOCAL_MACRO_HALO_UM:+-e OT_PRD_LOCAL_MACRO_HALO_UM=$OT_PRD_LOCAL_MACRO_HALO_UM} -e OT_PRD_UNFOLD_CHAINS=${OT_PRD_UNFOLD_CHAINS:-0} -e OT_PRD_TARGET_SLEW_PS=${OT_PRD_TARGET_SLEW_PS:-0} -e OT_PRD_TARGET_FANOUT=${OT_PRD_TARGET_FANOUT:-0} -e OT_PRD_AUTO_FANOUT=${OT_PRD_AUTO_FANOUT:-} -e OT_PRD_TIE_SPLIT=${OT_PRD_TIE_SPLIT:-1} -e OT_MAX_FANOUT=$OT_MAX_FANOUT -e OT_SLEW_MARGIN=$OT_SLEW_MARGIN \
    -e OT_SETUP_MARGIN=$OT_SETUP_MARGIN -e OT_HOLD_MARGIN=$OT_HOLD_MARGIN -e OT_HOLD_ALLOW_SETUP=$OT_HOLD_ALLOW_SETUP \
    -e OT_PRD_MAX_WIRE_LENGTH=${OT_PRD_MAX_WIRE_LENGTH:-0} -e "OT_PRD_PROTECT_NETS=${OT_PRD_PROTECT_NETS:-}" -e "OT_PRD_NARROW_PINS=${OT_PRD_NARROW_PINS:-}" -e OT_PRD_FROM=${OT_PRD_FROM:-grt} -e OT_HOLD_MAXBUF=$OT_HOLD_MAXBUF -e "OT_PAD_MASTERS=${OT_PAD_MASTERS:-}" -e OT_VCLK_CORNER=${OT_VCLK_CORNER:-} -e OT_PRD_NO_HOLD=${OT_PRD_NO_HOLD:-0} -e OT_PRD_REPAIR_RC=${OT_PRD_REPAIR_RC:-} ${OT_HOLD_REPAIR_SCOPE:+-e OT_HOLD_REPAIR_SCOPE=$OT_HOLD_REPAIR_SCOPE} \
    -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; $PATCH; \
    make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS do-route $ROUTE_CORNERS SKIP_INCREMENTAL_REPAIR=1; rc=\$?; \
    chown -R \$HUID:\$HGID /work; exit \$rc" > "$D/run_prd.log" 2>&1
  rc=$?
  $DK run --rm -v "$D":/work "$IMAGE" chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
  grep -h "^OT_PRD\|RSZ-00[0-9]*\|Inserted\|OT_CLK_FREEZE" $D/run/logs/asap7/*/base/5_1_grt.log 2>/dev/null | tail -n 16
  ck=-
  if [ $rc = 0 ]; then bash $D/clk_freeze_check.sh $D $IMAGE > $D/clk_freeze_check.log 2>&1; ck=$?; [ $ck = 0 ] || rc=5; fi
  ct="-"; cb="-"
  if [ $rc = 0 ]; then
    ct=$(count $D p${P}_tc TC 5_2_route_rcx.spef 1); cb=$(count $D p${P}_bc BC 5_2_route_rcx.spef 0); echo "$ct"; echo "$cb"
    [[ "$ct" == *"placement ok"* ]] || rc=6
  fi
  rev=$(grep -ho 'masters restored [0-9]*' $D/run/logs/asap7/*/base/5_1_grt.log 2>/dev/null | tail -n 1 | awk '{print $3}')
  st=$(echo "$ct" | awk '{print $4}'); sc=$(echo "$ct" | awk '{print $6}'); bt=$(echo "$cb" | awk '{print $4}'); bc=$(echo "$cb" | awk '{print $6}')
  addres pass=$P dir=$D route_rc=$rc clk_check_rc=$ck tc_slew=${st:--} tc_cap=${sc:--} bc_slew=${bt:--} bc_cap=${bc:--} sink_masters_restored=${rev:--}
  [ $rc = 0 ] || break
  if [ "$st$sc$bt$bc" = 0000 ] || [ $P -ge $MAXP ]; then FINAL=$D; break; fi
  B=$(ls -d $D/run/results/asap7/*/base)
  [ "${OT_PRD_FROM:-grt}" = final ] && OT_PRD_FROM=route   # pass p+1 of a final seed: pass p has no post-route edits
  N=${D0}_p$((P + 1))
  OT_SLEW_MARGIN="$OT_SLEW_MARGIN" OT_SETUP_MARGIN="$OT_SETUP_MARGIN" OT_HOLD_ALLOW_SETUP="$OT_HOLD_ALLOW_SETUP" OT_HOLD_MAXBUF="$OT_HOLD_MAXBUF" \
  OT_PRD_HOOK="$D/prd_hook.tcl" OT_PRD_TARGETED=${OT_PRD_TARGETED:-0} OT_PRD_UNFOLD_CHAINS=${OT_PRD_UNFOLD_CHAINS:-0} OT_PRD_TARGET_SLEW_PS=${OT_PRD_TARGET_SLEW_PS:-} OT_PRD_TARGET_FANOUT=${OT_PRD_TARGET_FANOUT:-} OT_PRD_AUTO_FANOUT=${OT_PRD_AUTO_FANOUT:-} OT_PRD_TIE_SPLIT=${OT_PRD_TIE_SPLIT:-} OT_PRD_FROM=${OT_PRD_FROM:-grt} OT_PRD_MAX_WIRE_LENGTH=${OT_PRD_MAX_WIRE_LENGTH:-0} OT_PRD_PROTECT_NETS="${OT_PRD_PROTECT_NETS:-}" OT_PRD_NARROW_PINS="${OT_PRD_NARROW_PINS:-}" OT_PRD_REPAIR_RC="${OT_PRD_REPAIR_RC:-}" OT_HOLD_REPAIR_SCOPE="${OT_HOLD_REPAIR_SCOPE:-}" bash $HERE/prd_mk.sh $D $N $V $SO $B/5_2_route_rcx.spef || { rc=7; break; }
  D=$N; P=$((P + 1))
done
if [ -n "$FINAL" ] && [ "${OT_PRD_FINISH:-1}" = 1 ]; then
  $DK run --rm --name prd-fin-$$ --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$FINAL":/work -w /OpenROAD-flow-scripts/flow \
    "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; $PATCH; \
    make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS do-finish $ROUTE_CORNERS" > $FINAL/run_prd_finish.log 2>&1
  rc=$?
  $DK run --rm -v "$FINAL":/work "$IMAGE" chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
  POST=-
  # OT_PRD_POST=0 (KW-ECO-1 eco_loop.py): finish only; the caller restores the kit config.mk and signs off itself
  if [ $rc = 0 ] && [ "${OT_PRD_POST:-1}" = 1 ]; then
    for r in run_kit_hbm.sh run_kit_kv.sh run_kit.sh; do
      # only runners with a sign-off-only GOAL=post (KV / HBM); others: the die owner signs off FINAL
      if [ -f $FINAL/$r ] && grep -qE 'GOAL ?!= ?post|GOAL=post' $FINAL/$r; then POST=$r; bash $FINAL/$r $FINAL post $MEM $CPUS > $FINAL/run_prd_post.log 2>&1; rc=$?; break; fi
    done
  fi
  addres final=1 dir=$FINAL finish_post_rc=$rc post_runner=$POST
fi
cat $RES
exit $rc
