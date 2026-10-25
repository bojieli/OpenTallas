#!/bin/bash
# KV-CORES 10-24: make a warm post-route ECO dir from a ROUTED KV core kit, on the host that holds the kit.
#   mk_eco.sh KIT OUT VARIANT SO_DIR
# OUT = new dir: the kit's files (not run/ views/ signoff/), its results base with 5_2_route.odb as 4_cts.odb +
# 6_final.spef + 1_2_yosys.v (+ 1_synth.v / clock_period / mem.json / ot_*.txt) and objects/, a 4_cts.sdc = the kit SDC +
# set_propagated_clock, the POST_GLOBAL_ROUTE hook eco_route.tcl, TC/BC libs, and SO_DIR's tools/die_plan
# signoff.py / face_guard.py / sdc_lint.py (the branch's sign-off with the hard-core latency contract).
# env OT_PAD_MASTERS='FAx1_ASAP7_75t_R:1': placement padding before the ECO legalization (DRT pin access)
# env OT_DRV_PLACE=1: DRV-first on placement parasitics, then incremental GRT, then timing repair on GRT parasitics
# env OT_DRV_LAST=1: hold/setup repair before the fanout/slew repair (eco_route.tcl; avoids RSZ-0074)
# VARIANT: b<N> FF-only (CORNER=BC), max_fanout 24, slew margin 20, hold margin N ps, setup may break at FF (TT gated)
#          m<N> MCMM tc+bc, max_fanout 24, slew margin 20, setup margin 10, hold margin N ps, allow setup
set -euo pipefail
KIT=$(cd "$1" && pwd); OUT=$2; V=$3; SO=$4
HERE=$(cd "$(dirname "$0")" && pwd)
test ! -e "$OUT" || { echo "mk_eco: $OUT exists (never relaunch into a run dir)"; exit 2; }
RS=$(ls -d $KIT/run/results/asap7/*/base); NICK=$(basename $(dirname $RS))
test -f $RS/5_2_route.odb -a -f $RS/6_final.spef || { echo "mk_eco: $RS lacks 5_2_route.odb / 6_final.spef"; exit 2; }
mkdir -p $OUT
rsync -a --exclude /run --exclude /views --exclude /signoff --exclude '/signoff_*' --exclude '/signoff*.log' --exclude '/run_*.log' --exclude /rc.txt $KIT/ $OUT/
B=$OUT/run/results/asap7/$NICK/base
mkdir -p $B $OUT/run/logs/asap7/$NICK/base $OUT/run/reports/asap7/$NICK/base $OUT/run/objects/asap7/$NICK/base
cp $RS/5_2_route.odb $B/4_cts.odb
for f in 6_final.spef 1_2_yosys.v 1_synth.v clock_period.txt mem.json ot_face_flops.txt ot_unreg_pins.txt; do
  test -f $RS/$f && cp $RS/$f $B/; done
rsync -a $KIT/run/objects/asap7/$NICK/base/ $OUT/run/objects/asap7/$NICK/base/ 2>/dev/null || true
{ cat $OUT/constraint.sdc; echo 'set_propagated_clock [all_clocks]'; } > $B/4_cts.sdc
cp $HERE/eco_route.tcl $OUT/
cp $HERE/../run_kit_kv.sh $HERE/../corners.tcl $HERE/../pin_audit_core.py $OUT/
cp $SO/tools/die_plan/signoff.py $SO/tools/die_plan/face_guard.py $SO/tools/die_plan/sdc_lint.py $OUT/
# macro (SRAM) liberty per corner: the CORNERS=... route reads only <CORNER>_LIB_FILES, so the kit's ADDITIONAL_LIBS
# (<macro>_tt.lib) must be added per corner (_tt -> TC, _ff -> BC; refuse if the _ff file is missing)
ML_TT=$(sed -n 's/^export ADDITIONAL_LIBS = //p' $OUT/config.mk)
ML_FF=$(echo "$ML_TT" | sed 's/_tt\.lib/_ff.lib/g')
for f in $ML_FF; do test -f "$OUT/${f#/work/}" || { echo "mk_eco: missing FF macro lib $f"; exit 2; }; done
cat >> $OUT/config.mk <<CFG
# KV-CORES warm post-route ECO (physical/die_plan/qwen_kvsys/cores/harden/eco, variant $V)
export POST_GLOBAL_ROUTE_TCL = /work/eco_route.tcl
export TC_LIB_FILES = \$(TC_NLDM_LIB_FILES) $ML_TT
export BC_LIB_FILES = \$(BC_NLDM_LIB_FILES) $ML_FF
override export PWR_NETS_VOLTAGES =
override export GND_NETS_VOLTAGES =
CFG
HM=${V:1}; [[ "$HM" =~ ^[0-9]+$ ]] || { echo "mk_eco: variant $V: want b<hold margin ps> or m<hold margin ps>"; exit 2; }
case ${V:0:1} in
  b) printf "OT_MAX_FANOUT=24\nOT_SLEW_MARGIN=20\nOT_SETUP_MARGIN=\nOT_HOLD_MARGIN=$HM\nOT_HOLD_ALLOW_SETUP=1\nOT_HOLD_MAXBUF=40\nROUTE_CORNERS='CORNER=BC CORNERS=bc'\n" ;;
  m) printf "OT_MAX_FANOUT=24\nOT_SLEW_MARGIN=20\nOT_SETUP_MARGIN=10\nOT_HOLD_MARGIN=$HM\nOT_HOLD_ALLOW_SETUP=1\nOT_HOLD_MAXBUF=40\nROUTE_CORNERS='CORNER=TC CORNERS=\"tc bc\"'\n" ;;
  *) echo "mk_eco: unknown variant $V"; exit 2 ;;
esac > $OUT/variant.env
[ -n "${OT_DRV_LAST:-}" ] && echo "OT_DRV_LAST=$OT_DRV_LAST" >> $OUT/variant.env
[ -n "${OT_DRV_PLACE:-}" ] && echo "OT_DRV_PLACE=$OT_DRV_PLACE" >> $OUT/variant.env
[ -n "${OT_RETIME_LAST:-}" ] && echo "OT_RETIME_LAST=$OT_RETIME_LAST" >> $OUT/variant.env
[ -n "${OT_PAD_MASTERS:-}" ] && echo "OT_PAD_MASTERS='$OT_PAD_MASTERS'" >> $OUT/variant.env
printf '{"variant": "%s", "source_kit": "%s:%s", "source_route": "%s/5_2_route.odb", "signoff_tools": "%s"}\n' \
  $V "$(hostname)" $KIT $RS "$SO" > $OUT/ECO.json
echo "eco ready $OUT ($(du -sh $OUT | cut -f1))"
