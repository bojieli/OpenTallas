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
cp $HERE/hold_route.tcl $HERE/eco_pre_grt.tcl $O/
# the kit's effective PRE_GLOBAL_ROUTE hook (last 'override export', else last 'export'), chained by eco_pre_grt.tcl
KPRE=$(grep -E '^override export PRE_GLOBAL_ROUTE_TCL' $O/config.mk | tail -n 1 | sed 's/.*= *//' || true)
[ -n "$KPRE" ] || KPRE=$(grep -E '^export PRE_GLOBAL_ROUTE_TCL' $O/config.mk | tail -n 1 | sed 's/.*= *//' || true)
# FLOW-CLKFREEZE 2026-10-27: clock lock sourced by hold_route.tcl + blocking clock-net geometry check (run_hold.sh)
ROOT=$(cd "$HERE/../../../../.." && pwd)
for f in clk_freeze.tcl clk_dump_db.tcl clk_geom_diff.py clk_freeze_check.sh; do cp "$ROOT/tools/die_plan/$f" $O/; done
cat >> $O/config.mk <<CFG
# QC-CORES warm hold ECO (ELEM-QK recipe b: FF-only, hold margin $MG)
# FLOW-CLKFREEZE 2026-10-27: 'override' (as KV mk_eco FLOW-TAG 10-26): QC kits set 'override export POST_GLOBAL_ROUTE_TCL'
# (core_flow / s5 hooks), which beat a plain export, so this hold ECO (and its clock lock) never ran
override export POST_GLOBAL_ROUTE_TCL = /work/hold_route.tcl
override export PRE_GLOBAL_ROUTE_TCL = /work/eco_pre_grt.tcl
export OT_KIT_PRE_GRT = $KPRE
CFG
printf "OT_HOLD_MARGIN=$MG\nOT_HOLD_ALLOW_SETUP=1\nOT_HOLD_MAXBUF=40\nROUTE_CORNERS='CORNER=BC CORNERS=bc'\n" > $O/variant.env
# FF-only session in the FF vclk frame when the kit binds one (SIGNOFF-MODES-2 finding; same as KV mk_eco variant b)
[ -f $O/vclk_corner.tcl ] && echo "OT_VCLK_CORNER=ff" >> $O/variant.env
python3 -I "$O/signoff.py" bundle "$O/so/tools/die_plan" || exit 1
printf '{"source_kit": "%s", "source_route": "%s/5_2_route.odb", "recipe": "ELEM-QK hold_eco b", "margin_ps": %s}\n' $K $RS $MG > $O/HOLD_ECO.json
echo "ready $O"
