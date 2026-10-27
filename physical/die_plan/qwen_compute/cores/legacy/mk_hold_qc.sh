#!/bin/bash
# QC-CORES: warm FF-only hold ECO (ELEM-QK recipe b, tools/elem_qk/hold_eco @ claude/elem-qk-1024) from a completed
# gen_core_kit_qc.py kit route on the same host.   mk_hold_qc.sh KITDIR OUTDIR [MARGIN=3] [GUIDE]
# FLOW-SHARED-4 2026-10-27 (COORD ruling 1): the ECO is ONE OpenROAD session (hold_1s.tcl via run_hold.sh), started from
# the kit's MATCHED final ODB + SPEF (6_final.odb/.spef of the same route; a local ECO can update 6_final without the 5_2
# checkpoint: VMR F4K 72 data cells) and that route's full guide file GUIDE (default <base>/route.guide; pass the newer
# one when a later ECO rewrote the guides, e.g. VMR F4K input/repair.guide).  The two-process do-5_1_grt / do-5_2_route
# hand-off (route segments or none) is retired for routed-DB ECOs.
set -euo pipefail
K=$(cd "$1" && pwd); O=$2; MG=${3:-3}; GD=${4:-}; HERE=$(cd "$(dirname "$0")" && pwd)
RS=$(ls -d $K/run/results/asap7/*/base); NICK=$(basename $(dirname $RS))
rm -rf $O; mkdir -p $O; rsync -a --exclude run --exclude signoff $K/ $O/
B=$O/run/results/asap7/$NICK/base; mkdir -p $B $O/run/logs/asap7/$NICK/base $O/run/reports/asap7/$NICK/base $O/run/objects/asap7/$NICK/base
test -s "$RS/6_final.odb" && test -s "$RS/6_final.spef" || { echo "QC_ECO FAIL: missing matched final ODB/SPEF"; exit 2; }
[ -n "$GD" ] || GD=$RS/route.guide
test -s "$GD" || { echo "QC_ECO FAIL: guide file $GD missing"; exit 2; }
[ "$GD" -nt "$RS/6_final.odb" ] || [ -n "${4:-}" ] || echo "QC_ECO WARN: $GD older than 6_final.odb (pass the matching guide as arg 4 if a later ECO rewrote it)"
cp "$RS/6_final.odb" "$B/4_cts.odb"; cp $RS/6_final.spef $RS/1_2_yosys.v $RS/1_synth.v $RS/clock_period.txt $B/
cp "$GD" "$B/route_src.guide"
rsync -a $K/run/objects/asap7/$NICK/base/ $O/run/objects/asap7/$NICK/base/
{ cat $O/constraint.sdc; echo 'set_propagated_clock [get_clocks clk]'; } > $B/4_cts.sdc
cp $HERE/hold_1s.tcl $O/
# the kit's effective PRE_GLOBAL_ROUTE hook (last 'override export', else last 'export'), sourced inside hold_1s.tcl
KPRE=$(grep -E '^override export PRE_GLOBAL_ROUTE_TCL' $O/config.mk | tail -n 1 | sed 's/.*= *//' || true)
[ -n "$KPRE" ] || KPRE=$(grep -E '^export PRE_GLOBAL_ROUTE_TCL' $O/config.mk | tail -n 1 | sed 's/.*= *//' || true)
# FLOW-CLKFREEZE 2026-10-27: clock lock sourced by hold_1s.tcl + blocking clock-net geometry check (run_hold.sh)
ROOT=$(cd "$HERE/../../../../.." && pwd)
for f in clk_freeze.tcl clk_dump_db.tcl clk_geom_diff.py clk_freeze_check.sh; do cp "$ROOT/tools/die_plan/$f" $O/; done
# kit PRE_GLOBAL_ROUTE hook (FF vclk bind) runs inside the one session (hold_1s.tcl), not as an ORFS stage hook
DRTP=generic; [ -f $O/f4g_pre_drt_sig.tcl ] && [ -f $O/m6_strip_f4g.txt ] && DRTP=f4g
printf "OT_HOLD_MARGIN=$MG\nOT_HOLD_ALLOW_SETUP=1\nOT_HOLD_MAXBUF=40\nROUTE_CORNERS='CORNER=BC CORNERS=bc'\nOT_KIT_PRE_GRT=$KPRE\nOT_QC_DRT_PREP=$DRTP\nOT_QC_GUIDE=/work/run/results/asap7/$NICK/base/route_src.guide\n" > $O/variant.env
# FF-only session in the FF vclk frame when the kit binds one (SIGNOFF-MODES-2 finding; same as KV mk_eco variant b)
[ -f $O/vclk_corner.tcl ] && echo "OT_VCLK_CORNER=ff" >> $O/variant.env
python3 -I "$O/signoff.py" bundle "$O/so/tools/die_plan" || exit 1
printf '{"source_kit": "%s", "source_route": "%s/6_final.odb", "guide": "%s", "recipe": "ELEM-QK hold_eco b, one session (hold_1s.tcl)", "drt_prep": "%s", "margin_ps": %s}\n' $K $RS $GD $DRTP $MG > $O/HOLD_ECO.json
echo "ready $O"
