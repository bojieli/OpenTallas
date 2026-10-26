#!/bin/bash
# QC-CORES: warm FF-only hold ECO (ELEM-QK recipe b, tools/elem_qk/hold_eco @ claude/elem-qk-1024) from a completed
# gen_core_kit_qc.py kit route on the same host.   mk_hold_qc.sh KITDIR OUTDIR [MARGIN=3]
set -euo pipefail
K=$(cd "$1" && pwd); O=$2; MG=${3:-3}; HERE=$(cd "$(dirname "$0")" && pwd)
RS=$(ls -d $K/run/results/asap7/*/base); NICK=$(basename $(dirname $RS))
rm -rf $O; mkdir -p $O; rsync -a --exclude run --exclude signoff $K/ $O/
B=$O/run/results/asap7/$NICK/base; mkdir -p $B $O/run/logs/asap7/$NICK/base $O/run/reports/asap7/$NICK/base $O/run/objects/asap7/$NICK/base
cp $RS/5_2_route.odb $B/4_cts.odb; cp $RS/6_final.spef $RS/1_2_yosys.v $RS/1_synth.v $RS/clock_period.txt $B/
rsync -a $K/run/objects/asap7/$NICK/base/ $O/run/objects/asap7/$NICK/base/
{ cat $O/constraint.sdc; echo 'set_propagated_clock [get_clocks clk]'; } > $B/4_cts.sdc
cp $HERE/hold_route.tcl $O/
cat >> $O/config.mk <<CFG
# QC-CORES warm hold ECO (ELEM-QK recipe b: FF-only, hold margin $MG)
export POST_GLOBAL_ROUTE_TCL = /work/hold_route.tcl
CFG
printf "OT_HOLD_MARGIN=$MG\nOT_HOLD_ALLOW_SETUP=1\nOT_HOLD_MAXBUF=40\nROUTE_CORNERS='CORNER=BC CORNERS=bc'\n" > $O/variant.env
mkdir -p $O/so/tools/die_plan; cp $O/signoff.py $O/sdc_lint.py $O/face_guard.py $O/pair_skew.tcl $O/so/tools/die_plan/; cp $O/clock_family.tcl $O/so/tools/die_plan/
printf '{"source_kit": "%s", "source_route": "%s/5_2_route.odb", "recipe": "ELEM-QK hold_eco b", "margin_ps": %s}\n' $K $RS $MG > $O/HOLD_ECO.json
echo "ready $O"
