#!/bin/bash
# DIE-QC-55 PROG rebuild chain (recipe of results/qc_die34_1029/prog: cand-2 prep -> ffh10 route -> [ffh10r FF ECO]) -> re-sign at flow-20261031-h-qc + LEC
set -uo pipefail
P=/srv/opentallas-scratch2/claude/die-qc-55/prog; K=$P/kit_v2; T=$P/tags/h-qc/tools/die_plan; C=16; M=40; IMAGE=openroad/orfs:asap7lock
NK=kq_qfd_dv_s8x_prog_pd40a0
st(){ echo "$(date "+%F %T") $*" >> $P/v2.status; }
route(){ # KIT NAME PRECMD CHECKARGS ENV
  local k=$1 n=$2 pre=$3 chk=$4 env=$5
  docker run --rm --name dqc55-$n --cpus=$C --memory=${M}g --memory-swap=${M}g -v "$k":/work $env -w /OpenROAD-flow-scripts/flow $IMAGE bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; rc=0; \
    $pre \
    if [ \$rc = 0 ]; then python3 -I /work/kit_modes.py check /work $chk || rc=9; fi; \
    if [ \$rc = 0 ] && grep -q \"OT_HOLD_MM = 1\" /work/config.mk && ! grep -q \"OT_HOLD_MM = 0\" /work/config.mk; then python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1 || { echo KIT_MODES FAIL orfs_hold_mm; rc=9; }; fi; \
    if [ \$rc = 0 ]; then for t in do-grt do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc do-6_1_fill do-6_1_fill.sdc do-6_report do-generate_abstract; do \
      make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$C \$t || { rc=\$?; echo STAGE_FAIL \$t rc \$rc; break; }; done; fi; \
    chown -R $(id -u):$(id -g) /work; exit \$rc" > "$k/run_route.log" 2>&1
}
signoff(){ SIGNOFF_DOCKER=docker python3 -I $T/signoff.py run --run-dir "$1/run" --kit "$1" --corners tt,ff --ff-vclk auto --out "$1/signoff" --image $IMAGE > "$1/signoff.log" 2>&1; grep -E "^SIGNOFF|^  - " "$1/signoff.log" | head -12 >> $P/v2.status; python3 -c "import json,sys;print(json.load(open(sys.argv[1]))[\"verdict\"])" "$1/signoff/signoff.json" 2>/dev/null; }
resign(){ python3 -I $T/resign.py run --kit "$1" --tag flow-20261031-h-qc --repo /srv/opentallas-scratch2/claude/wt/die-qc-55p --tools $T --out "$2" --build-commit $(git -C /srv/opentallas-scratch2/claude/wt/die-qc-55p rev-parse HEAD) --lane DIE-QC-55 --name "$3" --note "$4" > "$2.log" 2>&1; st "resign $2 rc=$?"; tail -5 "$2.log" >> $P/v2.status; }
st "A prep+ffh10 route start"
route $K v2a "openroad -exit /work/prep_prog.tcl > /work/prep.log 2>&1 || { echo PREP_FAIL; rc=7; }; grep -E \"^PREP|OT_PG\" /work/prep.log;" "--step grt --session \"tc bc\" --hold-repair" ""
rc=$?; st "A route rc=$rc"; grep -E "^PREP|STAGE_FAIL|OT_FINAL|FF_CONVERGE|overflow" $K/run_route.log | tail -8 >> $P/v2.status
[ $rc = 0 ] || exit 3
v=$(signoff $K); st "A signoff verdict=$v"
if [ "$v" = SIGNED ]; then resign $K $P/rs_v2 dqc55v2 "DIE-QC-55 rebuild: re-created native pin-reach FF move (prog_mover.py, 591 flops) + cand-2 prep + ffh10 route"; exit 0; fi
# ffh10r: FF-only post-route hold ECO from the ROUTED 5_2_route.odb + routed 6_final.spef (clock wires FIXED)
K2=$P/kit_v2r; rm -rf $K2; mkdir -p $K2; (cd $K && cp -r $(ls -A | grep -vE "^(run|signoff|in)$") $K2/)
R2=$K2/run/results/asap7/$NK/base; mkdir -p $R2 $K2/run/logs/asap7/$NK/base $K2/run/reports/asap7/$NK/base
cp $K/run/results/asap7/$NK/base/5_2_route.odb $R2/4_cts.odb; cp $K/run/results/asap7/$NK/base/6_final.spef $R2/; cp $K/run/results/asap7/$NK/base/5_route.sdc $R2/4_cts.sdc; cp $K/run/results/asap7/$NK/base/1_* $R2/ 2>/dev/null
cat /srv/opentallas-scratch2/claude/wt/die-qc-55p/results/qc_die34_1029/prog/ffh10e/config_append.mk >> $K2/config.mk
st "B ffh10r ECO start"
route $K2 v2r "" "--step eco --session bc --vclk-corner ff --hold-repair" "-e OT_VCLK_CORNER=ff"
rc=$?; st "B route rc=$rc"; grep -E "ECO_FFH|OT_CLK_FREEZE|STAGE_FAIL|KIT_MODES" $K2/run_route.log | tail -8 >> $P/v2.status
[ $rc = 0 ] || exit 4
v=$(signoff $K2); st "B signoff verdict=$v"
if [ "$v" = SIGNED ]; then resign $K2 $P/rs_v2r dqc55v2r "DIE-QC-55 rebuild: re-created native pin-reach FF move + cand-2 prep + ffh10 route + ffh10r FF-only hold ECO from routed DB (clock wires FIXED)"; exit 0; fi
exit 5
