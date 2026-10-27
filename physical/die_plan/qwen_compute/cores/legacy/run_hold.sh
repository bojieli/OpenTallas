#!/bin/bash
# ELEM-QK 10-24 / FLOW-SHARED-4 10-27: run one warm hold-ECO variant dir (made by mk_hold_qc.sh): ONE OpenROAD session
# (hold_1s.tcl through ORFS 'make run': incremental GRT + hold repair + DRT + fill + RCX, kit's own eco.tcl shape) in docker,
# then the BLOCKING clock-net geometry diff, main's tools/die_plan/signoff.py --corners tt,ff (D/signoff/signoff.json) and
# the routed LEC of 6_final_logic.v (D/lec_eco, runs whatever the sign-off verdict).
#   run_hold.sh D CPUS MEM_GB          (through ot-run)
# rc: 0 route+clock+signoff ran (verdict in signoff.json / lec), route rc != 0 -> that rc, 5 clock geometry changed.
set -uo pipefail
D=$(cd "$1" && pwd); CPUS=${2:-8}; MEM=${3:-32}
. $D/variant.env
IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}
DK=docker; docker ps >/dev/null 2>&1 || DK="sudo docker"
NAME=elemqk-hold-$(basename $(dirname $D))-$(basename $D)-$$
$DK run --rm --name "$NAME" --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$D":/work \
  -e HUID=$(id -u) -e HGID=$(id -g) -e OT_HOLD_MARGIN=$OT_HOLD_MARGIN -e OT_HOLD_ALLOW_SETUP=$OT_HOLD_ALLOW_SETUP \
  -e OT_HOLD_MAXBUF=$OT_HOLD_MAXBUF -e OT_VCLK_CORNER=${OT_VCLK_CORNER:-} -e OT_KIT_PRE_GRT=${OT_KIT_PRE_GRT:-} \
  -e OT_QC_DRT_PREP=${OT_QC_DRT_PREP:-generic} -e OT_QC_GUIDE=$OT_QC_GUIDE -e OT_QC_MAXADD=${OT_QC_MAXADD:-500} \
  -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS $ROUTE_CORNERS \
    RUN_SCRIPT=/work/hold_1s.tcl RUN_LOG_NAME_STEM=hold_1s run; rc=\$?; \
  chown -R \$HUID:\$HGID /work; exit \$rc" > "$D/run_hold.log" 2>&1
rc=$?
$DK run --rm -v "$D":/work "$IMAGE" chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
grep -q '^QC1S DONE' "$D/run_hold.log" || { [ $rc != 0 ] || rc=3; }
echo "route_finish_rc=$rc" > $D/rc.txt
grep -h "^QC1S\|OT_CLK_FREEZE\|RSZ-00[0-9]*\|Inserted\|Number of violations\|DRT-0199" $D/run_hold.log 2>/dev/null | tail -n 14
# FLOW-CLKFREEZE 2026-10-27: BLOCKING clock-net geometry diff (ECO input route vs final DB); change -> rc 5, no sign-off
if [ $rc = 0 ]; then
  bash $D/clk_freeze_check.sh $D $IMAGE > $D/clk_freeze_check.log 2>&1; ck=$?
  grep -h '^CLK_GEOM_DIFF' $D/clk_freeze_check.log | head -n 6; echo "clk_freeze_check_rc=$ck" >> $D/rc.txt
  [ $ck = 0 ] || rc=5
fi
if [ $rc = 0 ]; then
  SIGNOFF_DOCKER="$DK" python3 -I $D/so/tools/die_plan/signoff.py run --run-dir $D/run --kit $D --out $D/signoff \
    --corners tt,ff --image "$IMAGE" > $D/signoff.log 2>&1
  echo "signoff_rc=$?" >> $D/rc.txt
  grep -E '^SIGNOFF|^  - ' $D/signoff.log | head -12
fi
# routed LEC (logic export without TAPCELL/FILLER, as the kit's adopted F4K proof), independent of the sign-off verdict
V=$(ls $D/run/results/asap7/*/base/6_final_logic.v 2>/dev/null | head -1)
if [ -n "$V" ] && [ -f $D/lec.py ]; then
  R=${V#$D/}
  $DK run --rm --cpus 8 --memory 24g -v "$D":/work "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
    python3 -I /work/lec.py /work --netlist /work/$R --out /work/lec_eco; r=\$?; chown -R $(id -u):$(id -g) /work/lec_eco; exit \$r" > $D/lec_eco.log 2>&1
  echo "lec_rc=$?" >> $D/rc.txt; tail -n 1 $D/lec_eco.log
fi
exit $rc
