#!/bin/bash
# ELEM-QK 10-24: assemble warm hold-ECO variant dirs for a KV head core from its completed 285.12 route.
#   mk_hold.sh HEAD(e1..e7) SRCHOST RECOVERY_DIR SRC_KIT OUTROOT MAIN_SHA
# OUTROOT/<head>/{a,b,c}: kit files of the corner recovery (safe SDC), results = original 5_2_route.odb as
# 4_cts.odb + 6_final.spef + 1_2_yosys.v, a 4_cts.sdc from the safe SDC, BC/TC libs, POST_GLOBAL_ROUTE hook.
#   a: FF-only (CORNERS=bc) hold margin 0, FF setup may break (TT setup still gated at sign-off)
#   b: FF-only hold margin 3
#   c: MCMM tc+bc hold margin 0, setup guarded on both corners (no -allow_setup_violations)
set -euo pipefail
HD=$1; SH=$2; REC=$3; KIT=$4; OUT=$5; MAIN=$6
HERE=$(cd "$(dirname "$0")" && pwd); REPO=$(cd $HERE/../../.. && pwd)
B=$OUT/$HD/_base; rm -rf $B; mkdir -p $B
rsync -a --exclude views_safe --exclude run $SH:$REC/ $B/
RS=$(ssh -n $SH "ls -d $KIT/run/results/asap7/*/base"); NICK=$(basename $(dirname $RS))
mkdir -p $B/run/results/asap7/$NICK/base $B/run/logs/asap7/$NICK/base $B/run/reports/asap7/$NICK/base $B/run/objects/asap7/$NICK/base
rsync -a $SH:$RS/5_2_route.odb $B/run/results/asap7/$NICK/base/4_cts.odb
rsync -a $SH:$RS/6_final.spef $SH:$RS/1_2_yosys.v $SH:$RS/clock_period.txt $B/run/results/asap7/$NICK/base/
rsync -a $SH:$KIT/run/objects/asap7/$NICK/base/ $B/run/objects/asap7/$NICK/base/ 2>/dev/null || true
{ cat $B/constraint.sdc; echo 'set_propagated_clock [get_clocks clk]'; } > $B/run/results/asap7/$NICK/base/4_cts.sdc
cp $HERE/hold_route.tcl $B/
cat >> $B/config.mk <<CFG
# ELEM-QK warm hold ECO (tools/elem_qk/hold_eco)
export POST_GLOBAL_ROUTE_TCL = /work/hold_route.tcl
export TC_LIB_FILES = \$(TC_NLDM_LIB_FILES)
export BC_LIB_FILES = \$(BC_NLDM_LIB_FILES)
override export PWR_NETS_VOLTAGES =
override export GND_NETS_VOLTAGES =
CFG
mkdir -p $B/so && git -C $REPO archive $MAIN tools/die_plan | tar -x -C $B/so
for v in a b c; do
  rm -rf $OUT/$HD/$v; cp -a $B $OUT/$HD/$v
  case $v in
    a) printf "OT_HOLD_MARGIN=0\nOT_HOLD_ALLOW_SETUP=1\nOT_HOLD_MAXBUF=40\nROUTE_CORNERS='CORNER=BC CORNERS=bc'\n" ;;
    b) printf "OT_HOLD_MARGIN=3\nOT_HOLD_ALLOW_SETUP=1\nOT_HOLD_MAXBUF=40\nROUTE_CORNERS='CORNER=BC CORNERS=bc'\n" ;;
    c) printf "OT_HOLD_MARGIN=0\nOT_HOLD_ALLOW_SETUP=0\nOT_HOLD_MAXBUF=40\nROUTE_CORNERS='CORNER=TC CORNERS=tc\\\\ bc'\n" ;;
  esac > $OUT/$HD/$v/variant.env
  printf '{"head": "%s", "variant": "%s", "source_route": "%s:%s/5_2_route.odb", "sdc": "%s:%s/constraint.sdc", "main": "%s"}\n' \
    $HD $v $SH $RS $SH $REC $MAIN > $OUT/$HD/$v/HOLD_ECO.json
done
rm -rf $B
echo "$HD ready: $(du -sh $OUT/$HD | cut -f1)"
