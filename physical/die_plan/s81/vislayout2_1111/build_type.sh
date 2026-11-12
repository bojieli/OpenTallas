#!/bin/bash
# build_type.sh T PLAN TAG : VISLAYOUT2-S81 private full-flow build of one S81 type on a positions-only plan delta.
# Mirrors kit_wave run-item for S81 (spec e9eda32d41c col_h9_r2 a30): kit_rtl script (bind8) -> kit_topology
# prepare-stations -> gen.py phys (spec gen_env + OT_GRT_TRANSITION_MODE=edge_outline, gen_args) -> gen_lint ->
# kit_preflight --contract -> run_kit.sh route (synth..route..sign-off) through ot-run on epyc9.
set -uo pipefail; cd /
T=$1; PLAN0=$2; TAG=$3
B=/srv/opentallas-scratch2/claude/vislayout2-s81/b; W=$B/$TAG/$T
SRC=/srv/opentallas-scratch2/claude/kw43/src_t51f_pbp_por15c_por36
ASB=/srv/opentallas-scratch2/claude/type-safe-4/s81p3/asbuilt_f.json
LAND=/srv/opentallas-scratch2/claude/kw43t51/src_t51f/physical/die_plan/s81/h2_2249/landed_sidecar_h2.json
otr() { local m=$2; shift 6; ( cd $W && /usr/local/bin/ot-heavy --mem $m -- "$@" ); }  # local admission on epyc9 (ot-heavy = what ot-run runs there)
OTR=otr
rm -rf $W; mkdir -p $W/plandir
# plan dir of links (relative pins_file etc. resolve) + the candidate plan as a real file
for f in $SRC/physical/die_plan/s81/*; do ln -s "$f" $W/plandir/; done
rm -f $W/plandir/plan_vl2.json; cp $PLAN0 $W/plandir/plan_vl2.json; ln -sfn $W/plandir/plan_vl2.json $W/plandir/die_plan.json
PL=$W/plandir/plan_vl2.json
echo "BUILD $T tag=$TAG plan=$(sha256sum $PL | cut -c1-12) start $(date '+%F %T %Z')"
step() { local n=$1; shift; echo "== $n $(date +%T)"; "$@" > $W/$n.log 2>&1; local rc=$?; tail -3 $W/$n.log; [ $rc = 0 ] || { echo "STEP_FAIL $n rc=$rc"; exit $rc; }; }
step kit_rtl $OTR --mem 8 --threads 2 --dir $W bash -c "cd $SRC && TYPE=$T OUT=$W/rtl PLAN=$PL bash /srv/opentallas-scratch2/claude/kw42/kit_rtl_s81_final_1109.sh"
step kit_topology $OTR --mem 8 --threads 2 --dir $W bash -c "cd $SRC && OT_NATIVE_RESET_SCOPE=selected python3 -I tools/die_plan/kit_topology.py prepare-stations $PL $T $W/rtl --native-plan $PL --asbuilt $ASB"
step gen $OTR --mem 16 --threads 2 --dir $W bash -c "cd $SRC && export OT_FLOW_TAG=flow-20261108-eg-s81 OT_NATIVE_RESET_SCOPE=selected OT_POROUS_VIEWS=all OT_GRT_TRANSITION_MODE=edge_outline; python3 tools/die_plan/gen.py phys $PL --out $W/gen --types $T --rtl-root $SRC --kit-rtl $T=$W/rtl/kit_rtl.f --cland-pinslot all --hold-ff-margin 0 --max-wire-um 100 --clock-landing $LAND"
K=$W/gen/$T; test -f $K/config.mk || { echo "GEN_NO_KIT"; exit 9; }
cat $K/grt_transition_mode 2>/dev/null | sed 's/^/grt_transition_mode: /'
step gen_lint $OTR --mem 10 --threads 2 --dir $W bash -c "cd $SRC && python3 tools/die_plan/kit_gen_lint.py $K --plan-dir $W/plandir --mem 8"
step preflight $OTR --mem 8 --threads 2 --dir $W bash -c "cd $SRC && python3 tools/die_plan/kit_preflight.py $K --plan-dir $W/plandir --contract --out $W/preflight.json"
echo "== run_kit route $(date +%T)"
$OTR --mem 48 --threads 8 --dir $W bash $W/gen/run_kit.sh $K route 48 8 > $W/run_kit.log 2>&1; rc=$?
tail -20 $W/run_kit.log; echo "BUILD_END rc=$rc $(date '+%F %T %Z')"
