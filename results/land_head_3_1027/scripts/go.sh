#!/bin/bash
# LAND-HEAD-3 go.sh NAME: GRT incl clock (LAND-HEAD-1 sl300 recipe: signals M4-M7 adj 0.75, die ctree M8-M9, ONE global_route,
# 50 congestion iterations) TT then FF on the kit B/NAME/kit + native arrivals + landed_phase_ocv (shared model) + render.
set -u
WT=/srv/opentallas-scratch2/claude/wt/land-head-3; B=/srv/opentallas-scratch2/claude/land-head-3; O=$B/$1
J=/srv/opentallas-scratch2/claude/land-head-1/compose/fb1_lat.json
cd $WT; echo START $(date) code $(git -C $WT rev-parse --short HEAD)+dirty plan $(sha256sum $J | cut -c1-12) host $(hostname)
python3 tools/die_plan/die_trial.py render $O/kit --plan $J > $O/render.log 2>&1 || echo RENDER_FAIL
mkdir -p $O/clk; cp $O/kit/clock/{ctree.v,ctree.tcl,tree.json} $O/clk/; cp $O/clk/ctree.tcl $O/clk/ctree_ck89.tcl
for CORNER in TT FF; do
  CORNER=$CORNER ADJ=0.75 python3 $WT/results/fallback_head_1026/scripts/mk_combo_dcm.py $O/kit $O/clk $O/out_$CORNER > $O/mk_$CORNER.log 2>&1 || { echo MK_FAIL; tail $O/mk_$CORNER.log; exit 1; }
  docker run --rm --name lh3-$1-$CORNER-$$ --memory=40g --memory-swap=40g --cpus=8 -e CORNER=$CORNER -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM \
    -v $O/kit:/work:ro -v $O/out_$CORNER:/out openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$CORNER.log 2>&1; echo EXIT \$? >> /out/combo_$CORNER.log; chown -R $(id -u):$(id -g) /out"
  grep -E "^(M[1-9]|Total) " $O/out_$CORNER/combo_$CORNER.log | tail -10; echo "GRT-0113/4: $(grep -c "GRT-011[34]" $O/out_$CORNER/combo_$CORNER.log) iters: $(grep -c "congestion iteration\|GRT-0101\|Congestion iteration" $O/out_$CORNER/combo_$CORNER.log)"; tail -2 $O/out_$CORNER/combo_$CORNER.log
done
echo COMBO_DONE $(date)
python3 $WT/tools/s81_head/landed_phase_ocv.py $J $O --tools $WT/tools/die_plan --out $O/landed_ocv.json > $O/landed_ocv.log 2>&1; cat $O/landed_ocv.log | cut -c1-260
python3 $B/cat2.py $O $J 12
python3 tools/s81_head/fallback_land_report.py $J $O --png $O/landed.png > $O/report.log 2>&1; tail -5 $O/report.log
echo END $(date)
